"""Reusable form field widgets for data entry."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Label, Select


class FloatField(Horizontal):
    """A labeled float input field."""

    DEFAULT_CSS = """
    FloatField {
        height: 3;
        margin-bottom: 0;
    }
    FloatField Label {
        width: 22;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }
    FloatField Input {
        width: 1fr;
        height: 3;
    }
    """

    def __init__(
        self,
        label: str,
        field_id: str,
        placeholder: str = "",
        value: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._field_id = field_id
        self._placeholder = placeholder
        self._value = value

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Input(
            placeholder=self._placeholder,
            value=self._value,
            id=self._field_id,
            type="number",
        )

    @property
    def input(self) -> Input:
        return self.query_one(f"#{self._field_id}", Input)

    def get_value(self) -> float | None:
        """Return the float value, or None if empty/invalid."""
        text = self.input.value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None


class TextField(Horizontal):
    """A labeled text input field."""

    DEFAULT_CSS = """
    TextField {
        height: 3;
        margin-bottom: 0;
    }
    TextField Label {
        width: 22;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }
    TextField Input {
        width: 1fr;
        height: 3;
    }
    """

    def __init__(
        self,
        label: str,
        field_id: str,
        placeholder: str = "",
        value: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._field_id = field_id
        self._placeholder = placeholder
        self._value = value

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Input(
            placeholder=self._placeholder,
            value=self._value,
            id=self._field_id,
        )

    @property
    def input(self) -> Input:
        return self.query_one(f"#{self._field_id}", Input)

    def get_value(self) -> str:
        return self.input.value.strip()


class SelectField(Horizontal):
    """A labeled select/dropdown field."""

    DEFAULT_CSS = """
    SelectField {
        height: 3;
        margin-bottom: 0;
    }
    SelectField Label {
        width: 22;
        height: 3;
        content-align-vertical: middle;
        padding: 1 1 0 0;
    }
    SelectField Select {
        width: 1fr;
        height: 3;
    }
    """

    def __init__(
        self,
        label: str,
        field_id: str,
        options: list[tuple[str, str]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._label = label
        self._field_id = field_id
        self._options = options

    def compose(self) -> ComposeResult:
        yield Label(self._label)
        yield Select(
            [(text, value) for text, value in self._options],
            id=self._field_id,
        )

    def get_value(self) -> str | None:
        sel = self.query_one(f"#{self._field_id}", Select)
        if sel.value == Select.BLANK:
            return None
        return str(sel.value)
