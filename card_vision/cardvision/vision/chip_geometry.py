"""A narrow joint guard for candidates that are both large and horizontally wide."""


def oversized_and_wide(box: tuple[int,int,int,int], shape: tuple, cfg: dict) -> bool:
    """Leave small wide or large square candidates alone; thresholds are tunable."""
    if not cfg.get("large_wide_filter",True):
        return False
    _,_,width,height=box
    area_fraction=width*height/(shape[0]*shape[1])
    aspect=width/max(1,height)
    return (area_fraction>=cfg.get("large_wide_area_min",.028)
            and aspect>=cfg.get("large_wide_aspect_min",1.50))
