from collections import deque


class OrderQueue:
    """
    FIFO Queue using collections.deque.
    Represents the Customer Order Reception.
    Orders are processed in the order they arrive (first come, first served).
    """

    def __init__(self):
        self.queue = deque()
        self.order_counter = 1

    def enqueue(self, package_name, category):
        order_id = f"ORD-{self.order_counter:04d}"
        self.order_counter += 1
        order = {
            "id": order_id,
            "name": package_name,
            "category": category,
        }
        self.queue.append(order)
        return order

    def dequeue(self):
        if len(self.queue) == 0:
            return None
        return self.queue.popleft()

    def size(self):
        return len(self.queue)

    def is_empty(self):
        return len(self.queue) == 0

    def peek(self):
        if self.queue:
            return self.queue[0]
        return None

    def all_items(self):
        return list(self.queue)
