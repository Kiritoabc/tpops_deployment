from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .parser import manifest_to_tree


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def parse_manifest(request):
    """
    上传 manifest.yaml 文本或 JSON { "content": "..." } 进行解析（本地调试/预览）。
    """
    content = request.data.get("content")
    if content is None and request.FILES.get("file"):
        content = request.FILES["file"].read().decode("utf-8", errors="replace")
    if not content:
        return Response(
            {"error": "请提供 content 或上传 file"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    tree = manifest_to_tree(content)
    return Response(tree)
