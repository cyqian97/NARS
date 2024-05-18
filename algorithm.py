from collections import deque
from gap_classes import *


class algorithm_1:
    def __init__(self, gaps):
        self.vis_gaps = []
        self.gap_lists = {}
        self.gap_id_map = {}
        for gap in gaps:
            self.add_new_gap(gap.id)

    def __call__(self, event_info):
        if event_info.gap1_id in self.gap_id_map:
            gap1_id = self.gap_id_map[event_info.gap1_id]
        else:
            gap1_id = event_info.gap1_id

        if event_info.gap2_id in self.gap_id_map:
            gap2_id = self.gap_id_map[event_info.gap2_id]
        else:
            gap2_id = event_info.gap2_id

        if event_info.etype == GapEventType.A:
            self.add_new_gap(gap1_id, is_appear=True)

        elif event_info.etype == GapEventType.D:
            gap_list_1 = self.gap_lists[gap1_id]
            if gap_list_1.star_pointer.next.gap_id is None:
                gap_list_1.insert(END, NEXT)
            self.remove_invis_gap(gap1_id)

        elif event_info.etype == GapEventType.S:
            gap_list_1 = self.gap_lists[gap1_id]
            if gap_list_1.star_pointer.next.gap_id is None:
                gap_list_1.insert(gap2_id, NEXT)
                new_list = self.add_new_gap(gap2_id)
                new_list.add_pointer(gap1_id)
            else:
                gap2_id = (
                    gap_list_1.star_pointer.next.gap_id
                )  # use gap_id at previous merge
                gap_list_2 = self.gap_lists[gap2_id]
                gap_list_1.star_pointer.move_next()
                gap_list_2.add_star_pointer(gap1_id)
                self.vis_gaps.append(gap2_id)
                self.add_new_id_map(event_info.gap2_id, gap2_id)

        elif event_info.etype == GapEventType.M:
            gap_list_1 = self.gap_lists[gap1_id]
            if gap_list_1.star_pointer.prev.gap_id is None:
                gap_list_1.insert(gap2_id, PREV)
                gap_list_2 = self.gap_lists[gap2_id]
                gap_list_2.add_pointer(gap1_id)
                self.remove_invis_gap(gap2_id)
            else:
                self.remove_invis_gap(
                    gap2_id
                )  # use the latest gap id, since when it appears, we don't know its the previous one
                self.add_new_id_map(gap2_id, gap_list_1.star_pointer.prev.gap_id)
                gap_list_1.star_pointer.move_prev()

    def add_new_gap(self, gap_id, is_appear=False):
        assert (
            not gap_id in self.gap_lists
        ), f"ERROR: Cannot add new gap list. Gap #{gap_id} already exists."
        new_list = DoublyLinkedList()
        self.gap_lists[gap_id] = new_list
        self.vis_gaps.append(gap_id)
        if is_appear:
            new_list.insert(END, PREV)
        return new_list

    def add_new_id_map(self, gap_id_new, gap_id_old):
        if gap_id_new is not gap_id_old:
            self.gap_id_map[gap_id_new] = gap_id_old

    def remove_invis_gap(self, gap_id):
        assert (
            gap_id in self.vis_gaps
        ), f"ERROR: Cannot remove invisible gap. Gap #{gap_id} is not in {self.vis_gaps}"
        self.vis_gaps.remove(gap_id)
        self.gap_lists[gap_id].star_pointer = None

    def __str__(self):
        s = ""
        s += "Gap ID Map: " + str(self.gap_id_map) + "\n"
        for key, val in self.gap_lists.items():
            s += f"{key}: "
            s += str(val)
            s += "\n"
        return s


END = object()
PREV = object()
NEXT = object()
STAR = object()


class Node:
    __slots__ = ("gap_id", "next", "prev")

    def __init__(self, gap_id=None):
        self.gap_id = gap_id
        self.next = None
        self.prev = None

    def __str__(self):
        if self.gap_id == END:
            return " || "
        elif self.gap_id == None:
            return ""
        else:
            return f" [{self.gap_id}] "


class Pointer:
    __slots__ = ("gap_id", "next", "prev")

    def __init__(self, prev=None, next=None, gap_id=None):
        if prev is None:
            self.prev = Node()
        else:
            self.prev = prev
        if next is None:
            self.next = Node()
        else:
            self.next = next
        self.connect()
        self.gap_id = gap_id

    def __str__(self):
        if self.gap_id is not None:
            return f" ({self.gap_id}) "
        else:
            return " (*) "

    def move_next(self):
        self.prev = self.next
        self.next = self.next.next
        if self.next is None:
            self.next = Node()
            self.connect()
        # print(f"move_next: next node: {self.next}")

    def move_prev(self):
        self.next = self.prev
        self.prev = self.prev.prev
        if self.prev is None:
            self.prev = Node()
            self.connect()
        # print(f"move_prev: next node: {self.next}")

    def copy(self, gap_id=None):
        return Pointer(self.prev, self.next, gap_id)

    def connect(self):
        self.next.prev = self.prev
        self.prev.next = self.next


class DoublyLinkedList:
    def __init__(self):
        self.star_pointer = Pointer()
        self.pointers = {}  # Do not add star pointer to this dict
        self.head = self.star_pointer.prev

    def add_star_pointer(self, gap_id):
        assert (
            self.star_pointer is None
        ), f"ERROR: Cannot add star pointer. The star pointer is not None."
        pointer = self.pointers[gap_id]
        self.star_pointer = pointer.copy()

    def add_pointer(self, gap_id):
        new_pointer = self.star_pointer.copy(gap_id)
        self.pointers[gap_id] = new_pointer
        return new_pointer

    def insert(self, gap_id, side):
        # next: insert next, move next
        pointer = self.star_pointer
        assert side in (
            PREV,
            NEXT,
        ), f"ERROR: Cannot insert. side must be PREV or NEXT, but is {side}"
        if side == NEXT:
            pointer.next.gap_id = gap_id
            pointer.prev = pointer.next
            pointer.next = Node()
            pointer.connect()
            if self.head.gap_id is None:
                self.head = pointer.prev

            # print(f"insert: next node is none: {self.star_pointer.next is None}")
        else:
            pointer.prev.gap_id = gap_id
            pointer.next = pointer.prev
            pointer.prev = Node()
            pointer.connect()
            self.head = pointer.next
        # self.nodes.append(node)

    # def __repr__(self):
    #     print("DoublyLinkedList: ", end="")
    #     current_node = self.head
    #     while current_node.gap_id != None:
    #         for pointer in self.pointers:
    #             if pointer.next == current_node:
    #                 print(pointer, end='')
    #         print(current_node, end='')
    #         current_node = current_node.next

    def __str__(self):
        s = ""
        current_node = self.head
        is_star_added = False
        while current_node:
            if self.star_pointer and self.star_pointer.next == current_node:
                s += str(self.star_pointer)
                is_star_added = True
            for pointer in self.pointers.values():
                if pointer.next == current_node:
                    s += str(pointer)
            s += str(current_node)

            current_node = current_node.next
        if (not is_star_added) and self.star_pointer:
            s += str(self.star_pointer)
        return s
