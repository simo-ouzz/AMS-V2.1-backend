"""Repository layer for article DB operations."""
from typing import Optional

from django.db.models import QuerySet

from masterdata.models import article


def get_article_by_id(article_id: int) -> article:
    """Retrieve a single article by primary key. Raises article.DoesNotExist."""
    return article.objects.get(pk=article_id)


def list_articles_by_compte(compte) -> QuerySet:
    """Return all articles belonging to *compte* with common relations pre-loaded."""
    return (
        article.objects.filter(compte=compte)
        .select_related(
            "produit",
            "produit__categorie",
            "nature",
            "fournisseur",
            "marque",
        )
        .order_by("-id")
    )


def create_article(**validated_data) -> article:
    """Insert a new article row."""
    return article.objects.create(**validated_data)


def update_article(article_obj: article, **fields) -> article:
    """Partial-update *article_obj* with the given *fields* and save."""
    for attr, value in fields.items():
        setattr(article_obj, attr, value)
    article_obj.save()
    return article_obj


def delete_article_if_eligible(article_obj: article) -> bool:
    """Delete article only if ``qte == qte_recue``. Returns True on success."""
    if article_obj.qte == article_obj.qte_recue:
        article_obj.delete()
        return True
    return False
