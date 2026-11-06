"""Image upload endpoint that runs the local DenseNet checkpoint."""

from fastapi import APIRouter, Depends, File, UploadFile, status

from apps.auth.dependencies import UserInfo, get_current_user
from apps.common.openapi_responses import RESP_401, RESP_422, RESP_500, RESP_503
from config.logging import get_logger

from .. import schemas, services

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/images",
    response_model=schemas.DetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect tissue regions in an image",
    description=(
        "Choose an image (JPEG, PNG, GIF, or WEBP). The local DenseNet checkpoint "
        "`resolution_best_densenet_model.pth` scans it for dentin, enamel, and pulp. "
        "Requires a bearer access token. "
        "Time: O(n) sliding windows over the image · Space: O(n)"
    ),
    responses={
        200: {"description": "Detected tissue regions"},
        401: RESP_401,
        413: {"description": "Image exceeds the maximum upload size"},
        422: RESP_422,
        500: RESP_500,
        503: RESP_503,
    },
)
async def analyze_image(
    image: UploadFile = File(..., description="Radiograph or dental image to scan"),
    current_user: UserInfo = Depends(get_current_user),
) -> schemas.DetectionResponse:
    """Detect tissue regions in one uploaded image.

    Args:
        image: Chosen image file.
        current_user: Authenticated user.

    Returns:
        Boxes for dentin, enamel, and pulp.

    Raises:
        UnsupportedImageError: If the file is empty or not a supported image.
        ImageTooLargeError: If the file exceeds the configured limit.
        ModelNotFoundError: If the checkpoint file is missing.
    """
    data = await image.read()
    logger.info(
        "Detecting tissue regions",
        filename=image.filename,
        size_bytes=len(data),
        user_id=current_user.id,
    )
    return await services.analyze_image(
        filename=image.filename or "image",
        data=data,
    )
