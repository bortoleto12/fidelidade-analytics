"""Estilo visual único para todos os gráficos do projeto (matplotlib)."""
import matplotlib as mpl
import matplotlib.pyplot as plt

AZUL, LARANJA, VERDE_AGUA = "#2a78d6", "#eb6834", "#1baf7a"
CINZA, TEXTO, TEXTO_2, GRADE, FUNDO = "#a9a8a2", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
SEQ_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def aplicar_estilo() -> None:
    mpl.rcParams.update({
        "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
        "font.size": 10.5, "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlelocation": "left", "axes.titlepad": 14,
        "axes.edgecolor": GRADE, "axes.labelcolor": TEXTO_2, "text.color": TEXTO,
        "xtick.color": TEXTO_2, "ytick.color": TEXTO_2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRADE, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "lines.linewidth": 2, "legend.frameon": False,
    })


def brl(v: float, pos=None) -> str:
    """Formata valores em reais de forma compacta (R$ 1,2 mi / R$ 350 mil)."""
    if abs(v) >= 1e6:
        return f"R$ {v / 1e6:,.1f} mi".replace(".", ",")
    if abs(v) >= 1e3:
        return f"R$ {v / 1e3:,.0f} mil"
    return f"R$ {v:,.0f}"


def subtitulo(ax, texto: str) -> None:
    ax.text(0, 1.02, texto, transform=ax.transAxes, color=TEXTO_2, fontsize=10, va="bottom")


__all__ = ["aplicar_estilo", "brl", "subtitulo", "plt",
           "AZUL", "LARANJA", "VERDE_AGUA", "CINZA", "TEXTO", "TEXTO_2", "GRADE", "SEQ_AZUL"]
