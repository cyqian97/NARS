"""Gap Navigation Tree (GNT) algorithm — Section IV of Tovar et al. 2007."""

from backend.gap import GapEventType


# Sentinel and direction constants used by DoublyLinkedList.insert()
END = object()   # marks an unexplored branch terminus
PREV = object()  # insert/move toward the previous (older) side of history
NEXT = object()  # insert/move toward the next (newer) side of history


class GNT:
    """Maintains the Gap Navigation Tree as the robot moves.

    gap_lists      -- dict[gap_id -> DoublyLinkedList]: per-gap history list
    visible_gap_ids -- list[gap_id]: gaps currently in the robot's sensor
    gap_id_map     -- dict[new_id -> old_id]: remaps reused IDs after split/merge
    """

    def __init__(self, gaps):
        self.visible_gap_ids = []
        self.gap_lists = {}
        self.gap_id_map = {}
        for gap in gaps:
            self._add_gap(gap.id)

    def __call__(self, event_info):
        """Update the GNT for one topological event (A/D/S/M)."""
        gap1_id = self.gap_id_map.get(event_info.gap1_id, event_info.gap1_id)
        gap2_id = self.gap_id_map.get(event_info.gap2_id, event_info.gap2_id)

        if event_info.etype == GapEventType.A:
            # New gap appeared from behind an inflection point.
            self._add_gap(gap1_id, is_appear=True)

        elif event_info.etype == GapEventType.D:
            # Gap disappeared; seal the open end of its history list.
            gap_list = self.gap_lists[gap1_id]
            if gap_list.star_pointer.next.gap_id is None:
                gap_list.insert(END, NEXT)
            self._remove_gap(gap1_id)

        elif event_info.etype == GapEventType.S:
            # One gap splits into two.
            gap_list_1 = self.gap_lists[gap1_id]
            if gap_list_1.star_pointer.next.gap_id is None:
                # First time at this split: record gap2 as the new branch.
                gap_list_1.insert(gap2_id, NEXT)
                new_list = self._add_gap(gap2_id)
                new_list.add_pointer(gap1_id)
            else:
                # Revisiting a known split: restore the earlier gap2 id.
                gap2_id = gap_list_1.star_pointer.next.gap_id
                gap_list_2 = self.gap_lists[gap2_id]
                gap_list_1.star_pointer.move_next()
                gap_list_2.add_star_pointer(gap1_id)
                self.visible_gap_ids.append(gap2_id)
                self._add_id_map(event_info.gap2_id, gap2_id)

        elif event_info.etype == GapEventType.M:
            # Two gaps merge into one.
            gap_list_1 = self.gap_lists[gap1_id]
            if gap_list_1.star_pointer.prev.gap_id is None:
                # First time at this merge: record gap2 as the predecessor.
                gap_list_1.insert(gap2_id, PREV)
                gap_list_2 = self.gap_lists[gap2_id]
                gap_list_2.add_pointer(gap1_id)
                self._remove_gap(gap2_id)
            else:
                # Revisiting a known merge: reuse the stored predecessor.
                self._remove_gap(gap2_id)
                self._add_id_map(gap2_id, gap_list_1.star_pointer.prev.gap_id)
                gap_list_1.star_pointer.move_prev()

    def _add_gap(self, gap_id, is_appear=False):
        assert gap_id not in self.gap_lists, f"Gap #{gap_id} already exists."
        new_list = DoublyLinkedList()
        self.gap_lists[gap_id] = new_list
        self.visible_gap_ids.append(gap_id)
        if is_appear:
            new_list.insert(END, PREV)
        return new_list

    def _remove_gap(self, gap_id):
        assert gap_id in self.visible_gap_ids, f"Gap #{gap_id} is not visible."
        self.visible_gap_ids.remove(gap_id)
        self.gap_lists[gap_id].star_pointer = None

    def _add_id_map(self, new_id, old_id):
        if new_id is not old_id:
            self.gap_id_map[new_id] = old_id

    def __str__(self):
        lines = ["Gap ID Map: " + str(self.gap_id_map)]
        for gid, lst in self.gap_lists.items():
            lines.append(f"{gid}: {lst}")
        return "\n".join(lines)


class Node:
    __slots__ = ("gap_id", "next", "prev")

    def __init__(self, gap_id=None):
        self.gap_id = gap_id
        self.next = None
        self.prev = None

    def __str__(self):
        if self.gap_id is END:
            return " || "
        if self.gap_id is None:
            return ""
        return f" [{self.gap_id}] "


class Pointer:
    __slots__ = ("gap_id", "next", "prev")

    def __init__(self, prev=None, next=None, gap_id=None):
        self.prev = prev if prev is not None else Node()
        self.next = next if next is not None else Node()
        self.connect()
        self.gap_id = gap_id

    def __str__(self):
        return f" ({self.gap_id}) " if self.gap_id is not None else " (*) "

    def move_next(self):
        self.prev = self.next
        self.next = self.next.next
        if self.next is None:
            self.next = Node()
            self.connect()

    def move_prev(self):
        self.next = self.prev
        self.prev = self.prev.prev
        if self.prev is None:
            self.prev = Node()
            self.connect()

    def copy(self, gap_id=None):
        return Pointer(self.prev, self.next, gap_id)

    def connect(self):
        self.next.prev = self.prev
        self.prev.next = self.next


class DoublyLinkedList:
    """Records the sequential gap-neighbor history for one gap.

    star_pointer -- Pointer: current read/write head (None when gap is invisible)
    pointers     -- dict[gap_id -> Pointer]: branch points from past splits/merges
    head         -- Node: first node of the list (for iteration/display)
    """

    def __init__(self):
        self.star_pointer = Pointer()
        self.pointers = {}
        self.head = self.star_pointer.prev

    def add_star_pointer(self, gap_id):
        assert self.star_pointer is None, "Star pointer already set."
        pointer = self.pointers[gap_id]
        self.star_pointer = pointer.copy()

    def add_pointer(self, gap_id):
        new_pointer = self.star_pointer.copy(gap_id)
        self.pointers[gap_id] = new_pointer
        return new_pointer

    def insert(self, gap_id, side):
        assert side in (PREV, NEXT), f"side must be PREV or NEXT."
        pointer = self.star_pointer
        if side == NEXT:
            pointer.next.gap_id = gap_id
            pointer.prev = pointer.next
            pointer.next = Node()
            pointer.connect()
            if self.head.gap_id is None:
                self.head = pointer.prev
        else:
            pointer.prev.gap_id = gap_id
            pointer.next = pointer.prev
            pointer.prev = Node()
            pointer.connect()
            self.head = pointer.next

    def __str__(self):
        s = ""
        current = self.head
        star_added = False
        while current:
            if self.star_pointer and self.star_pointer.next == current:
                s += str(self.star_pointer)
                star_added = True
            for p in self.pointers.values():
                if p.next == current:
                    s += str(p)
            s += str(current)
            current = current.next
        if not star_added and self.star_pointer:
            s += str(self.star_pointer)
        return s
