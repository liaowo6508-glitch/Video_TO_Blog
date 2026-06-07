from __future__ import annotations

from debug_utils import debug_log
from pipelines.video_to_blog import video_to_blog_pipeline

# #region agent log
try:
    debug_log(
        location="pipelines/__init__.py:5",
        message="pipelines package imported",
        data={"exports": ["video_to_blog_pipeline"]},
        hypothesis_id="H2",
    )
except Exception:
    pass
# #endregion

__all__ = ["video_to_blog_pipeline"]
