import typing as t
from pydantic import BaseModel, root_validator, validator
from pydantic.generics import GenericModel
from ice.paper import Paper


def _to_str(paper: Paper, start: int, end: int) -> str:
    return " ".join(list(paper.sentences())[start:end])


class Selection(BaseModel):
    p: Paper
    start: int
    end: int

    # TODO: validate on creation

    def context(self, pre: int, post: int):
        idxs_before = range(max(0, self.start - pre), self.start)
        idxs_after = range(
            self.end, min(len(list(self.p.sentences())), self.end + post)
        )
        before = [
            Selection(p=self.p, start=start, end=start + 1) for start in idxs_before
        ]
        after = [Selection(p=self.p, start=end - 1, end=end) for end in idxs_after]
        return before, after

    def __str__(self):
        return _to_str(self.p, self.start, self.end)


def make_selector(paper: Paper) -> t.Callable[[int, int], Selection]:
    def s(start: int, end: int) -> Selection:
        return Selection(p=paper, start=start, end=end)

    return s


def sentences(paper: Paper) -> t.Sequence[Selection]:
    s = make_selector(paper)
    return [s(start, start + 1) for start in range(0, len(list(paper.sentences())))]


class Decontext(Selection):
    question: str | None
    out: str

    def __str__(self):
        return self.out


class Trace(BaseModel):
    components: t.Sequence[str | Selection]


T = t.TypeVar("T")


class Beam(GenericModel, t.Generic[T]):
    ...