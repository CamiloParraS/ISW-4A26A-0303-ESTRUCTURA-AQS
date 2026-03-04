from constants import CATEGORIES


class WarehouseInventory:
    """
    ARRAY representing fixed physical shelf positions in the warehouse.
    Each index corresponds to a category aisle.
    """

    def __init__(self):
        # ARRAY with fixed size — one slot per category
        self.shelves = [[] for _ in CATEGORIES]

    def get_aisle_index(self, category):
        return CATEGORIES.index(category)

    def store_package(self, package):
        idx = self.get_aisle_index(package["category"])
        self.shelves[idx].append(package)

    def get_packages_in_aisle(self, category):
        idx = self.get_aisle_index(category)
        return list(self.shelves[idx])

    def remove_package_from_aisle(self, category):
        idx = self.get_aisle_index(category)
        if len(self.shelves[idx]) > 0:
            return self.shelves[idx].pop(0)
        return None

    def count_in_aisle(self, category):
        idx = self.get_aisle_index(category)
        return len(self.shelves[idx])

    def total_packages(self):
        total = 0
        for slot in self.shelves:
            total += len(slot)
        return total

    def check_shelf(self, category):
        idx = self.get_aisle_index(category)
        packages = self.shelves[idx]
        return idx, packages

    def remove_specific_package(self, pkg_id: str) -> bool:
        """
        Remove a package by its exact ID from whichever aisle it lives in.
        Returns True if found and removed, False otherwise.
        Used by the priority-based truck loader so it can pull the exact
        packages it already scored and sorted
        """
        for aisle in self.shelves:  # self.shelves is a list of lists
            for i, pkg in enumerate(aisle):
                if pkg["id"] == pkg_id:
                    aisle.pop(i)
                    return True
        return False
