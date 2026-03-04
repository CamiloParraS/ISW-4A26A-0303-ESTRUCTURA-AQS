class Truck:
    """
    LIFO Stack using a Python list.
    Represents the truck loading bay.
    The LAST package loaded is the FIRST one delivered (top of stack).
    """

    def __init__(self):
        self.stack = []
        self.max_capacity = 20

    def push(self, package):
        if len(self.stack) >= self.max_capacity:
            return False, "Truck is full! (max 20 packages)"
        self.stack.append(package)
        return True, "OK"

    def pop(self):
        if len(self.stack) == 0:
            return None
        return self.stack.pop()

    def peek(self):
        if self.stack:
            return self.stack[-1]
        return None

    def size(self):
        return len(self.stack)

    def is_empty(self):
        return len(self.stack) == 0

    def is_full(self):
        return len(self.stack) >= self.max_capacity

    def all_items(self):
        # Return with top-of-stack first, reversed for display
        return list(reversed(self.stack))
