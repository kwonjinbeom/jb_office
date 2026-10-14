"""계층을 한 번에 읽어 경로와 하위 ID를 만든다. 깊이에 따른 DB 쿼리는 없다."""
def decorate_tree(nodes):
    nodes = list(nodes)
    by_id = {node.pk: node for node in nodes}
    for node in nodes:
        parts, ids, seen = [], [], set()
        current = node
        while current and current.pk not in seen:
            seen.add(current.pk)
            parts.append(current.name)
            ids.append(current.pk)
            current = by_id.get(current.parent_id)
        node.path = " / ".join(reversed(parts))
        node.ancestor_ids = ids
        node.depth = len(parts) - 1
    return sorted(nodes, key=lambda node: (node.path, node.pk))


def subtree_ids(nodes, pk):
    return [node.pk for node in nodes if pk in node.ancestor_ids]
