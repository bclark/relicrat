"""Read-only browsing groups and filters; never establish catalog identity."""
from fastapi import HTTPException
from sqlalchemy import Numeric,cast,func,or_,select
from relicrat.models import OwnedCopy,CatalogItem,Release
from relicrat.collection_types import COLLECTION_TYPES


def group_value(collection_type):
    config=COLLECTION_TYPES[collection_type].grouping
    if config is None:raise HTTPException(422,'This collection type has no configured groups')
    field={'artist':OwnedCopy.record_details['artist'].astext,'title':OwnedCopy.provisional_title}[config.field]
    return func.nullif(func.btrim(field),'')


def copies_query(q=None,collection_type=None,storage_location_id=None,unassigned=False,group=None):
    if storage_location_id is not None and unassigned:
        raise HTTPException(422,'Choose a storage location or unassigned copies, not both')
    if group is not None and collection_type not in ('comic','record','movie'):
        raise HTTPException(422,'Choose Albums, Comics or Movies before filtering a group')
    stmt=select(OwnedCopy).where(OwnedCopy.deleted_at.is_(None))
    if collection_type is not None:stmt=stmt.where(OwnedCopy.collection_type==collection_type)
    if storage_location_id is not None:stmt=stmt.where(OwnedCopy.storage_location_id==storage_location_id)
    if unassigned:stmt=stmt.where(OwnedCopy.storage_location_id.is_(None))
    if group is not None:
        value=group_value(collection_type)
        stmt=stmt.where(value==group if group else value.is_(None))
    if q and (term:=q.strip()):
        stmt=stmt.outerjoin(CatalogItem,OwnedCopy.catalog_item_id==CatalogItem.id).outerjoin(Release,OwnedCopy.release_id==Release.id).where(or_(
            OwnedCopy.provisional_title.icontains(term,autoescape=True),
            OwnedCopy.description.icontains(term,autoescape=True),
            OwnedCopy.barcode['value'].astext.icontains(term,autoescape=True),
            OwnedCopy.record_details['artist'].astext.icontains(term,autoescape=True),
            OwnedCopy.record_details['format'].astext.icontains(term,autoescape=True),
            OwnedCopy.comic_details['issue_number'].astext.icontains(term,autoescape=True),
            OwnedCopy.comic_details['publisher'].astext.icontains(term,autoescape=True),
            OwnedCopy.movie_details['media_format'].astext.icontains(term,autoescape=True),
            OwnedCopy.movie_details['studio'].astext.icontains(term,autoescape=True),
            OwnedCopy.edition_label.icontains(term,autoescape=True),
            CatalogItem.canonical_name.icontains(term,autoescape=True),
            Release.name.icontains(term,autoescape=True)))
    return stmt


def copy_order(collection_type,group):
    order=COLLECTION_TYPES[collection_type].grouping.order if group is not None and collection_type else None
    if order=='title':
        return (func.lower(OwnedCopy.provisional_title).asc().nulls_last(),OwnedCopy.provisional_title.asc().nulls_last(),OwnedCopy.id)
    if order=='issue_number':
        issue=func.nullif(func.btrim(OwnedCopy.comic_details['issue_number'].astext),'')
        prefix=cast(func.substring(func.ltrim(issue,'#'),'^[0-9]+'),Numeric)
        return (prefix.asc().nulls_last(),func.lower(issue).asc().nulls_last(),issue.asc().nulls_last(),OwnedCopy.id)
    return (OwnedCopy.created_at.desc(),OwnedCopy.id.desc())
