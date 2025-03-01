class SoldItem:
    """
    This class represents an item being sold in the game.
    :ivar price: The price of the item.
    :ivar uuid: The UUID of the item.
    :ivar name: The name of the item.
    """

    def __init__(self, price: int, uuid: str, name: str) -> None:
        """
        Initializes a SoldItem object.
        :param price:
        :param uuid:
        :param name:
        """
        self.price = price
        self.uuid = uuid
        self.name = name

    def __getitem__(self, item: int) -> int | str:
        """
        Makes a SoldItem object behave like a list. Necessary for backwards compatibility.
        :param item:
        :return:
        """
        map_ = {
            0: self.price,
            1: self.uuid,
            2: self.name
        }
        return map_[item]

    def __iter__(self) -> iter:
        """
        Makes a SoldItem iterate like a list. Necessary for backwards compatibility.
        :return: iter object
        """
        return iter([self.price, self.uuid, self.name])
