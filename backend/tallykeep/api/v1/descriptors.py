"""Descriptor endpoints — spec module 04. Stubs land in M4 (CRUD) and M5 (scan/derive)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from tallykeep.api.v1._stubs import not_implemented_response


router = APIRouter(tags=["descriptors"])


@router.get("/descriptors", status_code=501)
async def list_descriptors(holding_id: UUID | None = None) -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="GET /api/v1/descriptors"
    )


@router.post("/descriptors", status_code=501)
async def create_descriptor() -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="POST /api/v1/descriptors"
    )


@router.get("/descriptors/{descriptor_id}", status_code=501)
async def get_descriptor(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="GET /api/v1/descriptors/{id}"
    )


@router.patch("/descriptors/{descriptor_id}", status_code=501)
async def patch_descriptor(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="PATCH /api/v1/descriptors/{id}"
    )


@router.delete("/descriptors/{descriptor_id}", status_code=501)
async def delete_descriptor(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="DELETE /api/v1/descriptors/{id}"
    )


@router.post("/descriptors/{descriptor_id}/rescan", status_code=501)
async def rescan_descriptor(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="POST /api/v1/descriptors/{id}/rescan"
    )


@router.get("/descriptors/{descriptor_id}/addresses", status_code=501)
async def list_descriptor_addresses(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M4", route="GET /api/v1/descriptors/{id}/addresses"
    )


@router.post(
    "/descriptors/{descriptor_id}/addresses/next-receiving", status_code=501
)
async def next_receiving_address(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M4",
        route="POST /api/v1/descriptors/{id}/addresses/next-receiving",
    )


@router.get("/descriptors/{descriptor_id}/utxos", status_code=501)
async def list_descriptor_utxos(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/descriptors/{id}/utxos"
    )


@router.get("/descriptors/{descriptor_id}/balance", status_code=501)
async def descriptor_balance(descriptor_id: UUID) -> JSONResponse:
    return not_implemented_response(
        milestone="M5", route="GET /api/v1/descriptors/{id}/balance"
    )
