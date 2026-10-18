from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from .db import collection
from .schemas import DocumentCreate, DocumentOut, DocumentUpdate
from .utils import parse_id, serialize_document, utc_now

router = APIRouter(prefix="/api/documents", tags=["HW6 MongoDB documents"])


def _documents():
    return collection("clinical_trials")


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate):
    now = utc_now()
    document = payload.model_dump()
    document.update(created_at=now, updated_at=now)
    try:
        result = _documents().insert_one(document)
        return serialize_document(_documents().find_one({"_id": result.inserted_id}))
    except PyMongoError as error:
        raise HTTPException(500, "MongoDB error while creating document") from error


@router.get("", response_model=list[DocumentOut])
def list_documents():
    try:
        return [serialize_document(doc) for doc in _documents().find().sort("created_at", -1)]
    except PyMongoError as error:
        raise HTTPException(500, "MongoDB error while listing documents") from error


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: str):
    try:
        object_id = parse_id(document_id)
    except ValueError as error:
        raise HTTPException(400, "Invalid document id") from error
    document = _documents().find_one({"_id": object_id})
    if not document:
        raise HTTPException(404, "Document not found")
    return serialize_document(document)


@router.put("/{document_id}", response_model=DocumentOut)
def update_document(document_id: str, payload: DocumentUpdate):
    try:
        object_id = parse_id(document_id)
    except ValueError as error:
        raise HTTPException(400, "Invalid document id") from error
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(400, "At least one field is required")
    updates["updated_at"] = utc_now()
    result = _documents().update_one({"_id": object_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(404, "Document not found")
    return serialize_document(_documents().find_one({"_id": object_id}))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: str):
    try:
        object_id = parse_id(document_id)
    except ValueError as error:
        raise HTTPException(400, "Invalid document id") from error
    result = _documents().delete_one({"_id": object_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Document not found")
    return None

