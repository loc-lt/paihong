import io
import os
import re

import ezdxf
import matplotlib
import pymupdf
from ezdxf.addons.drawing import Frontend, RenderContext

from core.services.converter_pipeline.pipeline import process_svg_string

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend  # noqa: E402


class FileToSvgConverter:
    @staticmethod
    def process_file(file_bytes: bytes, filename: str) -> tuple[list[str], str]:
        """
        Routes the uploaded file to the appropriate converter based on its extension.
        Returns a tuple containing a list of individual SVGs and one combined SVG.
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
    def _convert_pdf_or_ai(file_bytes: bytes) -> tuple[list[str], str]:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        list_svg = []
        raw_full_svgs = []

        for page in doc:
            # Extract the raw SVG string from the PDF page
            full_svg = page.get_svg_image()
            raw_full_svgs.append(full_svg)

            # Run the geometric pipeline to split by region
            regional_svgs = process_svg_string(full_svg)
            list_svg.extend(regional_svgs)

        doc.close()

        # `svg_full` is simply the original, unmodified SVG (stacked if multi-page).
        # This provides a fallback for the user if the auto-split isn't satisfactory.
        svg_full = FileToSvgConverter._combine_svgs_vertically(raw_full_svgs)

        return list_svg, svg_full

    @staticmethod
    def _convert_dxf(
        file_bytes: bytes, units_per_inch: float = 25.4
    ) -> tuple[list[str], str]:
        """
        Converts a DXF drawing into an SVG string using matplotlib.
        Uses in-memory geometric processing to extract separated regions.
        """
        try:
            doc = ezdxf.read(io.StringIO(file_bytes.decode("utf-8")))
        except UnicodeDecodeError:
            doc = ezdxf.read(io.StringIO(file_bytes.decode("cp1252")))

        msp = doc.modelspace()

        # Render the entire DXF layout with Matplotlib
        fig = plt.figure()
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_aspect("equal")
        ax.axis("off")

        backend = MatplotlibBackend(ax)
        Frontend(RenderContext(doc), backend).draw_layout(msp, finalize=True)

        # Scale the figure to the actual drawing dimensions
        ax.autoscale(enable=True, tight=True)
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        width = max(xmax - xmin, 1e-9)
        height = max(ymax - ymin, 1e-9)
        fig.set_size_inches(width / units_per_inch, height / units_per_inch)

        # Export SVG into a string buffer
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

        # Extract small details via the geometric pipeline
        list_svg = process_svg_string(full_svg)

        # `svg_full` is the raw, unmodified SVG for fallback purposes.
        svg_full = full_svg

        return list_svg, svg_full

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
            # Extract width and height from the standard SVG tag
            match = re.search(r'viewBox="([^"]+)"', svg)
            if match:
                vb_parts = match.group(1).split()
                if len(vb_parts) == 4:
                    w = float(vb_parts[2])
                    h = float(vb_parts[3])

                    # Wrap the original SVG inside a group with a vertical translation
                    nested_svgs.append(
                        f'<g transform="translate(0, {total_height})">{svg}</g>'
                    )

                    total_height += h
                    max_width = max(max_width, w)

        # Wrap everything in a master SVG tag
        full_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {max_width} {total_height}" '
            f'width="{max_width}" height="{total_height}">\n'
            + "\n".join(nested_svgs)
            + "\n</svg>"
        )
        return full_svg
