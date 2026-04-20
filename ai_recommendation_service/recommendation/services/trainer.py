"""BiLSTM trainer for next-product recommendation from interaction logs."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from django.conf import settings
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.layers import Bidirectional, Concatenate, Dense, Dropout, Embedding, Input, LSTM
from tensorflow.keras.metrics import SparseTopKCategoricalAccuracy
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.preprocessing.sequence import pad_sequences

from tracking.models import EventLog

logger = logging.getLogger(__name__)

ACTION_ID_MAP = {
    'view': 1,
    'click': 2,
    'add_to_cart': 3,
}
EVENT_TO_ACTION = {
    EventLog.EventType.PRODUCT_VIEW: 'view',
    EventLog.EventType.PRODUCT_CLICK: 'click',
    EventLog.EventType.ADD_TO_CART: 'add_to_cart',
    EventLog.EventType.PURCHASE: 'add_to_cart',
}


def _to_dataframe() -> pd.DataFrame:
    rows = list(
        EventLog.objects.filter(
            event_type__in=list(EVENT_TO_ACTION.keys()),
            product_id__isnull=False,
        )
        .values('user_id', 'product_id', 'event_type', 'timestamp')
        .order_by('user_id', 'timestamp')
    )
    if not rows:
        return pd.DataFrame(columns=['user_id', 'product_id', 'action', 'timestamp'])
    df = pd.DataFrame(rows)
    df['action'] = df['event_type'].map(EVENT_TO_ACTION)
    df = df[['user_id', 'product_id', 'action', 'timestamp']]
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def _build_sequences(df: pd.DataFrame, max_len: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray, LabelEncoder]:
    if df.empty:
        raise RuntimeError('Không có interaction để huấn luyện BiLSTM.')
    df = df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
    df['time_gap'] = (
        df.groupby('user_id')['timestamp']
        .diff()
        .dt.total_seconds()
        .fillna(0)
    )
    df['new_session'] = (df['time_gap'] > 1800).astype(int)
    df['session_id'] = df.groupby('user_id')['new_session'].cumsum()
    df['action_id'] = df['action'].map(ACTION_ID_MAP).astype(int)

    product_encoder = LabelEncoder()
    df['product_id_enc'] = product_encoder.fit_transform(df['product_id']) + 1

    x_action: List[np.ndarray] = []
    x_product: List[np.ndarray] = []
    y: List[int] = []
    for _, group in df.groupby(['user_id', 'session_id']):
        actions = group['action_id'].values
        products = group['product_id_enc'].values
        if len(group) < 2:
            continue
        for i in range(1, len(group)):
            x_action.append(actions[:i])
            x_product.append(products[:i])
            y.append(int(products[i]))
    if not y:
        raise RuntimeError('Không đủ chuỗi session để tạo dữ liệu train BiLSTM.')

    x_action_np = pad_sequences(x_action, maxlen=max_len, padding='pre', truncating='pre')
    x_product_np = pad_sequences(x_product, maxlen=max_len, padding='pre', truncating='pre')
    y_np = np.asarray(y, dtype=np.int32)
    return x_action_np, x_product_np, y_np, product_encoder


def _build_model(max_len: int, num_products: int) -> Model:
    input_action = Input(shape=(max_len,))
    input_product = Input(shape=(max_len,))

    action_emb = Embedding(input_dim=4, output_dim=8)(input_action)
    product_emb = Embedding(input_dim=num_products, output_dim=64)(input_product)
    merged = Concatenate()([action_emb, product_emb])

    x = Bidirectional(LSTM(128))(merged)
    x = Dropout(0.2)(x)
    x = Dense(128, activation='relu')(x)
    x = Dropout(0.2)(x)
    output = Dense(num_products, activation='softmax')(x)

    model = Model(inputs=[input_action, input_product], outputs=output)
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy', SparseTopKCategoricalAccuracy(k=10, name='top10_acc')],
    )
    return model


def run_full_training_pipeline() -> Dict[str, Any]:
    ml = settings.RECOMMENDATION_ML
    max_len = int(ml['MAX_SEQUENCE_LEN'])
    epochs = int(ml['TRAIN_EPOCHS'])
    batch_size = int(ml['BATCH_SIZE'])

    df = _to_dataframe()
    x_action, x_product, y, encoder = _build_sequences(df, max_len=max_len)
    num_products = len(encoder.classes_) + 1

    uniq, counts = np.unique(y, return_counts=True)
    stratify = y if (len(uniq) > 1 and counts.min() >= 2) else None
    x_a_train, x_a_test, x_p_train, x_p_test, y_train, y_test = train_test_split(
        x_action,
        x_product,
        y,
        test_size=0.2,
        random_state=42,
        stratify=stratify,
    )

    model = _build_model(max_len=max_len, num_products=num_products)
    early_stop = EarlyStopping(monitor='val_loss', patience=3, restore_best_weights=True)
    model.fit(
        [x_a_train, x_p_train],
        y_train,
        validation_split=0.2,
        epochs=epochs,
        batch_size=batch_size,
        callbacks=[early_stop],
        verbose=1,
    )
    loss, acc, top10 = model.evaluate([x_a_test, x_p_test], y_test, verbose=0)

    model_path = Path(ml['MODEL_PATH'])
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model.save(model_path)

    metadata = {
        'max_len': max_len,
        'action_id_map': ACTION_ID_MAP,
        'product_classes': [int(x) for x in encoder.classes_.tolist()],
    }
    metadata_path = Path(ml['MODEL_METADATA_PATH'])
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=True), encoding='utf-8')

    metrics = {
        'test_loss': float(loss),
        'top1_acc': float(acc),
        'top10_acc': float(top10),
        'num_samples': int(len(y)),
        'num_products': int(num_products - 1),
    }
    logger.info('BiLSTM train done: %s', metrics)
    return {'status': 'ok', 'metrics': metrics}
