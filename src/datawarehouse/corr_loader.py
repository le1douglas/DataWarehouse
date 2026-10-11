# corr_loader.py
from datawarehouse.loader import Loader


class CorrLoader(Loader):
    """
    The Loader of the corrections layer.

    Unlike BrnzLoader it adds no metadata columns:
    meta_reviewed_by and meta_reviewed_date_time are filled in by the reviewer, in the source.
    //TODO: if we want to add a meta_reviewed_date_time column, we can do it here, but it will be the time of loading, not the time of reviewing.
    """
