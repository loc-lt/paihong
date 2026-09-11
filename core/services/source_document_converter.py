import io
import os
import re

import ezdxf
import fitz
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend


class FileToSvgConverter:
    VALID_EXTENSIONS = (".pdf", ".ai", ".dxf")

    @staticmethod
    def validate_extension(filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in FileToSvgConverter.VALID_EXTENSIONS:
            raise ValueError(
                "Invalid file extension. Please upload one of: "
                f"{', '.join(FileToSvgConverter.VALID_EXTENSIONS)}"
            )
        return ext

    @staticmethod
    def process_file(file_bytes: bytes, filename: str) -> tuple[list[str], str]:
        """
        Convert .pdf / .ai / .dxf into SVG strings.

        Returns:
            (list_svg, svg_full)
            - list_svg: one SVG per page/component (each becomes a Part)
            - svg_full: combined SVG stacked vertically
        """
        ext = FileToSvgConverter.validate_extension(filename)
        if ext == ".dxf":
            return FileToSvgConverter._convert_dxf(file_bytes)
        if ext in (".pdf", ".ai"):
            return FileToSvgConverter._convert_pdf_or_ai(file_bytes)
        raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _convert_pdf_or_ai(file_bytes: bytes) -> tuple[list[str], str]:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        list_svg = [page.get_svg_image() for page in doc]
        doc.close()
        svg_full = FileToSvgConverter._combine_svgs_vertically(list_svg)
        return list_svg, svg_full

    @staticmethod
    def _convert_dxf(
        file_bytes: bytes,
        units_per_inch: float = 25.4,
    ) -> tuple[list[str], str]:
        try:
            doc = ezdxf.read(io.StringIO(file_bytes.decode("utf-8")))
        except UnicodeDecodeError:
            doc = ezdxf.read(io.StringIO(file_bytes.decode("cp1252")))

        msp = doc.modelspace()
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_aspect("equal")
        ax.axis("off")
        backend = MatplotlibBackend(ax)
        Frontend(RenderContext(doc), backend).draw_layout(msp, finalize=True)
        ax.autoscale(enable=True, tight=True)
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        width = max(xmax - xmin, 1e-9)
        height = max(ymax - ymin, 1e-9)
        fig.set_size_inches(width / units_per_inch, height / units_per_inch)

        svg_buffer = io.StringIO()
        fig.savefig(
            svg_buffer,
            format="svg",
            transparent=True,
            bbox_inches="tight",
            pad_inches=0,
        )
        plt.close(fig)
        svg_str = svg_buffer.getvalue()
        return [svg_str], svg_str

    @staticmethod
    def _combine_svgs_vertically(svg_strings: list[str]) -> str:
        if not svg_strings:
            return ""
        if len(svg_strings) == 1:
            return svg_strings[0]

        total_height = 0
        max_width = 0
        nested_svgs = []
        for svg in svg_strings:
            match = re.search(r'viewBox="([^"]+)"', svg)
            if match:
                vb_parts = match.group(1).split()
                if len(vb_parts) == 4:
                    w = float(vb_parts[2])
                    h = float(vb_parts[3])
                    nested_svgs.append(
                        f'<g transform="translate(0, {total_height})">{svg}</g>'
                    )
                    total_height += h
                    max_width = max(max_width, w)

        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {max_width} {total_height}" '
            f'width="{max_width}" height="{total_height}">\n'
            + "\n".join(nested_svgs)
            + "\n</svg>"
        )
