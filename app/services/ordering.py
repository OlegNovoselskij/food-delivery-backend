from app.exceptions import InvalidOrdering


def apply_order(items: list, ids: list[int]) -> None:
    by_id = {item.id: item for item in items}
    if set(ids) != set(by_id):
        raise InvalidOrdering()
    for position, item_id in enumerate(ids):
        by_id[item_id].position = position
