import io
import os
import re
import tempfile

import ezdxf
import matplotlib
import pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext

from core.services.converter_pipeline.pipeline import process_svg_string

matplotlib.use("Agg")
matplotlib.rcParams["svg.fonttype"] = "none"

import matplotlib.pyplot as plt  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402


class FileToSvgConverter:
    @staticmethod
    def process_file(
        file_bytes: bytes, filename: str
    ) -> tuple[list[str], list[list[str]], str]:
        """
        Routes the uploaded file to the appropriate converter based on its extension.
        Returns a tuple containing a list of individual SVGs, texts per SVG,
        and one combined SVG.
        """
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".dxf":
            return FileToSvgConverter._convert_dxf(file_bytes)
        elif ext in [".pdf", ".ai"]:
            # Note: .ai files must be saved with "Create PDF Compatible File" checked
            # in Adobe Illustrator for pymupdf to parse them successfully.
            return FileToSvgConverter._convert_pdf_or_ai(file_bytes)
        else:
            raise ValueError(
                f"Unsupported file format: {ext}. Allowed: .pdf, .ai, .dxf"
            )

    @staticmethod
    def _convert_pdf_or_ai(
        file_bytes: bytes,
    ) -> tuple[list[str], list[list[str]], str]:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        list_svg = []
        list_texts = []
        raw_full_svgs = []

        for page in doc:
            # Extract the raw SVG string from the PDF page, keeping text as <text>
            full_svg = page.get_svg_image(text_as_path=False)
            raw_full_svgs.append(full_svg)

            regional_svgs, regional_texts = process_svg_string(full_svg)
            list_svg.extend(regional_svgs)
            list_texts.extend(regional_texts)

        doc.close()

        # `svg_full` is simply the original, unmodified SVG (stacked if multi-page).
        # This provides a fallback for the user if the auto-split isn't satisfactory.
        svg_full = FileToSvgConverter._combine_svgs_vertically(raw_full_svgs)

        return list_svg, list_texts, svg_full

    @staticmethod
    def _convert_dxf(
        file_bytes: bytes, units_per_inch: float = 25.4
    ) -> tuple[list[str], list[list[str]], str]:
        """
        Converts a DXF drawing into an SVG string using matplotlib.
        Uses in-memory geometric processing to extract separated regions.
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            doc = ezdxf.readfile(tmp_path)
        finally:
            os.remove(tmp_path)

        msp = doc.modelspace()

        # Render the entire DXF layout with Matplotlib
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_aspect("equal")
        ax.axis("off")

        backend = MatplotlibBackend(ax)
        Frontend(RenderContext(doc), backend).draw_layout(msp, finalize=True)

        # Inject DXF texts into the Matplotlib figure as invisible elements
        # so they can be processed and split by region_splitter.py
        dxf_texts = FileToSvgConverter._get_all_dxf_texts(msp)
        for text_str, x, y in dxf_texts:
            if text_str.strip():
                ax.text(x, y, text_str.strip(), color="none", alpha=0.0)

        # Scale the figure to the actual drawing dimensions
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

        full_svg = svg_buffer.getvalue()

        list_svg, list_texts = process_svg_string(full_svg)
        svg_full = full_svg

        return list_svg, list_texts, svg_full

    @staticmethod
    def _get_all_dxf_texts(layout, base_matrix=None) -> list[tuple[str, float, float]]:
        """
        Recursively extract all texts and their global coordinates from a DXF layout.
        """
        from ezdxf.math import Matrix44

        if base_matrix is None:
            base_matrix = Matrix44()

        texts = []
        for entity in layout:
            if entity.dxftype() == "TEXT":
                pos = base_matrix.transform(entity.dxf.insert)
                texts.append((entity.dxf.text, pos.x, pos.y))
            elif entity.dxftype() == "MTEXT":
                pos = base_matrix.transform(entity.dxf.insert)
                texts.append((entity.text, pos.x, pos.y))
            elif entity.dxftype() == "INSERT":
                if layout.doc and layout.doc.blocks:
                    block = layout.doc.blocks.get(entity.dxf.name)
                    if block:
                        new_matrix = entity.matrix44() @ base_matrix
                        texts.extend(
                            FileToSvgConverter._get_all_dxf_texts(block, new_matrix)
                        )
        return texts

    @staticmethod
    def _combine_svgs_vertically(svg_strings: list[str]) -> str:
        """
        Combines multiple SVG strings into a single vertically stacked SVG.
        """
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

        full_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {max_width} {total_height}" '
            f'width="{max_width}" height="{total_height}">\n'
            + "\n".join(nested_svgs)
            + "\n</svg>"
        )
        return full_svg
