import replik.console as console


class IdFinder:
    def __init__(self, max: int):
        assert max > 10
        self.ids = list(range(max))

    def take_next(self):
        """take the next free id"""
        if len(self.ids) == 0:
            console.fail("run out of ids! Exiting...")
            exit(1)
        return self.ids.pop(0)

    def give_back(self, id: int):
        """give back the id so that it can be re-used"""
        self.ids.insert(0, id)