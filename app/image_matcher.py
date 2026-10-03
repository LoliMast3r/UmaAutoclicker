"""Match captured frames against the sprite templates in the images folder."""

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from controller import ClickController
from screen_capture import CapturedFrame


logger = logging.getLogger(__name__)
DEFAULT_TEMPLATE_DIRECTORY = Path(__file__).resolve().parent.parent / "images"
SUPPORTED_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


@dataclass(frozen=True)
class SpriteMatch:
    template_name: str
    confidence: float
    bounding_box: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[int, int]:
        x, y, width, height = self.bounding_box
        return x + width // 2, y + height // 2


@dataclass(frozen=True)
class _Template:
    name: str
    image: np.ndarray
    mask: np.ndarray


class ImageMatcher:
    """Match each captured frame and click the best above-threshold result."""

    def __init__(
        self,
        controller: ClickController,
        template_directory: str | Path = DEFAULT_TEMPLATE_DIRECTORY,
        confidence_threshold: float = 0.85,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0 and 1")

        self.controller = controller
        self.confidence_threshold = confidence_threshold
        self.templates = self._load_templates(Path(template_directory))

    def on_frame(self, frame: CapturedFrame) -> SpriteMatch | None:
        """Process a capture callback and click once if a template matches."""
        match = self.find_match(frame)
        if match is not None:
            self.controller.on_match(*match.center)
        return match

    def find_match(self, frame: CapturedFrame) -> SpriteMatch | None:
        """Return the strongest match only when its score is greater than k."""
        image = frame.image
        if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
            raise ValueError("Captured image must be an 8-bit BGR image")

        frame_height, frame_width = image.shape[:2]
        best_match = None

        for template in self.templates:
            template_height, template_width = template.image.shape[:2]
            if template_height > frame_height or template_width > frame_width:
                continue

            scores = cv2.matchTemplate(
                image,
                template.image,
                cv2.TM_CCORR_NORMED,
                mask=template.mask,
            )
            _, confidence, _, location = cv2.minMaxLoc(scores)
            if not np.isfinite(confidence) or confidence <= self.confidence_threshold:
                continue

            local_x, local_y = location
            origin_x, origin_y = frame.screen_origin
            match = SpriteMatch(
                template_name=template.name,
                confidence=confidence,
                bounding_box=(
                    origin_x + local_x,
                    origin_y + local_y,
                    template_width,
                    template_height,
                ),
            )
            if best_match is None or match.confidence > best_match.confidence:
                best_match = match

        return best_match

    @staticmethod
    def _load_templates(directory: Path) -> tuple[_Template, ...]:
        templates = []
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in SUPPORTED_IMAGE_EXTENSIONS:
                continue

            image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            if image is None:
                logger.warning("Skipping unreadable sprite template: %s", path)
                continue

            if image.ndim == 2:
                template_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                mask = np.full(image.shape, 255, dtype=np.uint8)
            elif image.shape[2] == 4:
                template_image = image[:, :, :3]
                mask = np.where(image[:, :, 3] > 0, 255, 0).astype(np.uint8)
            elif image.shape[2] == 3:
                template_image = image
                mask = np.full(image.shape[:2], 255, dtype=np.uint8)
            else:
                logger.warning("Skipping unsupported sprite template: %s", path)
                continue

            if not np.any(mask):
                logger.warning("Skipping fully transparent sprite template: %s", path)
                continue

            templates.append(_Template(path.name, template_image, mask))

        if not templates:
            raise FileNotFoundError(f"No readable sprite templates found in {directory}")
        return tuple(templates)