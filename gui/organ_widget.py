"""
Organ widget for displaying player organs with status.
"""

import tkinter as tk
from tkinter import ttk

from game.game_engine import GameEngine
from game.models import OrganCard
from game.player import Player


class OrganWidget(ttk.Frame):
    """Widget for displaying an organ with its status."""

    def __init__(self, parent, organ: OrganCard, engine: GameEngine,
                 main_window, player: Player):
        super().__init__(parent)
        self.organ = organ
        self.engine = engine
        self.main_window = main_window
        self.player = player

        self._create_layout()

    def _create_layout(self):
        """Create the organ display layout."""
        # Determine organ status and colors
        if self.organ.is_removed:
            bg_color = '#e74c3c'  # Red for removed
            fg_color = 'white'
            status_text = "REMOVED"
        elif self.organ.is_protected:
            bg_color = '#2ecc71'  # Green for protected
            fg_color = 'white'
            status_text = "PROTECTED"
        else:
            bg_color = '#f39c12'  # Orange for normal
            fg_color = 'white'
            status_text = "HEALTHY"

        # Main frame with colored background
        self.configure(style='Organ.TFrame')

        # Create inner frame for content
        inner_frame = tk.Frame(
            self, bg=bg_color, relief='raised', borderwidth=2)
        inner_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Organ name
        name_label = tk.Label(inner_frame, text=self.organ.organ_type,
                              bg=bg_color, fg=fg_color,
                              font=('Arial', 10, 'bold'))
        name_label.pack(pady=2)

        # Status
        status_label = tk.Label(inner_frame, text=status_text,
                                bg=bg_color, fg=fg_color,
                                font=('Arial', 8))
        status_label.pack()

        # Vital indicator
        if self.organ.is_vital and not self.organ.is_removed:
            vital_label = tk.Label(inner_frame, text="VITAL",
                                   bg=bg_color, fg='yellow',
                                   font=('Arial', 7, 'bold'))
            vital_label.pack()

        # Protection source (if protected)
        if self.organ.is_protected and self.organ.protection_source:
            protection_label = tk.Label(inner_frame,
                                        text=f"({self.organ.protection_source})",
                                        bg=bg_color, fg=fg_color,
                                        font=('Arial', 6))
            protection_label.pack()

        # Configure minimum size
        inner_frame.configure(width=80, height=60)

        # Tooltip
        self._setup_tooltip(inner_frame)

    def _setup_tooltip(self, widget):
        """Setup tooltip for organ details."""
        def show_tooltip(event):
            tooltip = tk.Toplevel(self)
            tooltip.wm_overrideredirect(True)

            x = self.winfo_rootx() + 20
            y = self.winfo_rooty() + 20
            tooltip.geometry(f"+{x}+{y}")

            # Tooltip content
            tooltip_text = f"{self.organ.organ_type}\n\n"
            tooltip_text += f"Status: {self._get_status_text()}\n"
            tooltip_text += f"Vital: {'Yes' if self.organ.is_vital else 'No'}\n"
            tooltip_text += f"Can be protected: {'Yes' if self.organ.can_be_protected else 'No'}\n"

            if self.organ.is_protected and self.organ.protection_source:
                tooltip_text += f"Protected by: {self.organ.protection_source}"

            label = tk.Label(tooltip, text=tooltip_text,
                             background='lightyellow', relief='solid',
                             borderwidth=1, font=('Arial', 9),
                             justify=tk.LEFT)
            label.pack()

            # Auto-hide after delay
            def hide_tooltip(event=None):
                tooltip.destroy()

            tooltip.after(3000, hide_tooltip)
            widget.tooltip = tooltip

        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def _get_status_text(self) -> str:
        """Get human-readable status text."""
        if self.organ.is_removed:
            return "Removed/Destroyed"
        elif self.organ.is_protected:
            return "Protected"
        else:
            return "Healthy"
