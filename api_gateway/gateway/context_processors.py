from .services import CustomerGatewayService


def current_customer(request):
    """Expose the current customer object to all templates."""
    raw_customer_id = request.session.get('current_customer_id')
    customer_id = raw_customer_id if isinstance(raw_customer_id, int) else None

    if customer_id is None and isinstance(raw_customer_id, str) and raw_customer_id.isdigit():
        customer_id = int(raw_customer_id)

    if not customer_id:
        return {'current_customer': None}

    return {
        'current_customer': CustomerGatewayService.get_customer_by_id(customer_id),
    }
