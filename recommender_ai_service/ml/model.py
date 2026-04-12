"""
NextProductPredictor — LSTM-based sequential recommendation model.

Architecture:
    Input per timestep: (event_type_id, product_id, category_id, brand_id)
    ↓
    Multi-head embedding:
        E_event(8) + E_product(64) + E_category(16) + E_brand(16) = 104-dim
    ↓
    LSTM(input=104, hidden=256, layers=2, dropout=0.2)
    ↓
    Dropout(0.2) → Linear(256 → num_products)
    ↓
    Softmax → Top-K product indices

Design decisions:
- padding_idx=0 in all embeddings (PAD token)
- Pack/pad sequences for variable-length batches (avoid computing on padding)
- predict_top_k() excludes PAD (index 0) from output
"""
import torch
import torch.nn as nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class NextProductPredictor(nn.Module):
    """
    LSTM model predicting the next product a user will interact with.

    Args:
        vocab (dict): Vocabulary sizes with keys:
            - num_events      (int)
            - num_products    (int)
            - num_categories  (int)
            - num_brands      (int)
        config (dict): Architecture hyper-parameters with keys:
            - embed_event, embed_product, embed_category, embed_brand
            - hidden, layers, dropout
    """

    def __init__(self, vocab: dict, config: dict):
        super().__init__()

        self.vocab = vocab
        self.config = config

        # ── Embeddings ─────────────────────────────────────────────────────
        self.embed_event = nn.Embedding(
            vocab['num_events'] + 1,    # +1 for PAD (idx 0)
            config['embed_event'],
            padding_idx=0,
        )
        self.embed_product = nn.Embedding(
            vocab['num_products'] + 1,
            config['embed_product'],
            padding_idx=0,
        )
        self.embed_category = nn.Embedding(
            vocab['num_categories'] + 1,
            config['embed_category'],
            padding_idx=0,
        )
        self.embed_brand = nn.Embedding(
            vocab['num_brands'] + 1,
            config['embed_brand'],
            padding_idx=0,
        )

        embed_total = (
            config['embed_event']
            + config['embed_product']
            + config['embed_category']
            + config['embed_brand']
        )

        # ── LSTM ───────────────────────────────────────────────────────────
        self.lstm = nn.LSTM(
            input_size=embed_total,
            hidden_size=config['hidden'],
            num_layers=config['layers'],
            batch_first=True,
            dropout=config['dropout'] if config['layers'] > 1 else 0.0,
        )

        # ── Output head ────────────────────────────────────────────────────
        self.dropout = nn.Dropout(config['dropout'])
        self.fc = nn.Linear(config['hidden'], vocab['num_products'] + 1)

        self._init_weights()

    def _init_weights(self):
        """Xavier init for embeddings; orthogonal for LSTM."""
        for emb in (self.embed_event, self.embed_product, self.embed_category, self.embed_brand):
            nn.init.xavier_uniform_(emb.weight)
            emb.weight.data[0].zero_()  # keep PAD embedding = 0

        for name, param in self.lstm.named_parameters():
            if 'weight_ih' in name:
                nn.init.xavier_uniform_(param)
            elif 'weight_hh' in name:
                nn.init.orthogonal_(param)
            elif 'bias' in name:
                nn.init.zeros_(param)

        nn.init.xavier_uniform_(self.fc.weight)
        nn.init.zeros_(self.fc.bias)

    def forward(
        self,
        event_types: torch.Tensor,   # (B, T)
        product_ids: torch.Tensor,   # (B, T)
        category_ids: torch.Tensor,  # (B, T)
        brand_ids: torch.Tensor,     # (B, T)
        lengths: torch.Tensor = None,  # (B,) actual sequence lengths
    ) -> torch.Tensor:
        """
        Returns:
            logits: (B, num_products+1) — raw unnormalised scores
        """
        # ── Embed ──────────────────────────────────────────────────────────
        e_ev = self.embed_event(event_types)       # (B, T, E_e)
        e_pr = self.embed_product(product_ids)     # (B, T, E_p)
        e_ca = self.embed_category(category_ids)   # (B, T, E_c)
        e_br = self.embed_brand(brand_ids)         # (B, T, E_b)

        x = torch.cat([e_ev, e_pr, e_ca, e_br], dim=-1)  # (B, T, embed_total)

        # ── Pack sequences (skip padding in LSTM) ─────────────────────────
        if lengths is not None:
            x = pack_padded_sequence(x, lengths.cpu(), batch_first=True, enforce_sorted=False)

        lstm_out, _ = self.lstm(x)

        if lengths is not None:
            lstm_out, _ = pad_packed_sequence(lstm_out, batch_first=True)

        # ── Extract last valid hidden state per sequence ───────────────────
        if lengths is not None:
            # lengths is (B,); gather the output at position (length-1) for each item
            idx = (lengths - 1).clamp(min=0).long()             # (B,)
            idx = idx.unsqueeze(1).unsqueeze(2)                  # (B,1,1)
            idx = idx.expand(-1, 1, lstm_out.size(2))            # (B,1,H)
            last_out = lstm_out.gather(1, idx).squeeze(1)        # (B, H)
        else:
            last_out = lstm_out[:, -1, :]                        # (B, H)

        # ── Project to product vocab ───────────────────────────────────────
        last_out = self.dropout(last_out)
        logits = self.fc(last_out)                               # (B, V)
        return logits

    @torch.no_grad()
    def predict_top_k(
        self,
        event_types: torch.Tensor,
        product_ids: torch.Tensor,
        category_ids: torch.Tensor,
        brand_ids: torch.Tensor,
        lengths: torch.Tensor = None,
        k: int = 5,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            top_indices: (B, k) — product vocab indices
            top_probs:   (B, k) — softmax probabilities
        """
        self.eval()
        logits = self.forward(event_types, product_ids, category_ids, brand_ids, lengths)
        # Mask out PAD token (index 0) to never recommend it
        logits[:, 0] = float('-inf')
        probs = torch.softmax(logits, dim=-1)
        top_probs, top_indices = torch.topk(probs, k=k, dim=-1)
        return top_indices, top_probs


def build_model_config(ml_settings: dict) -> dict:
    """Convert Django ML_SETTINGS dict to model config dict."""
    return {
        'embed_event': ml_settings['EMBED_DIM_EVENT'],
        'embed_product': ml_settings['EMBED_DIM_PRODUCT'],
        'embed_category': ml_settings['EMBED_DIM_CATEGORY'],
        'embed_brand': ml_settings['EMBED_DIM_BRAND'],
        'hidden': ml_settings['LSTM_HIDDEN'],
        'layers': ml_settings['LSTM_LAYERS'],
        'dropout': ml_settings['LSTM_DROPOUT'],
    }
