from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.helpers import (
    delete_by_id,
    get_by_id,
    in_ids_sql,
    insert_from_body,
    paginate,
    parse_ids,
    serialize_row,
    serialize_rows,
    update_from_body,
    update_status_by_ids,
)
from app.common.auth import get_current_admin
from app.common.response import success
from app.database import execute, fetch_all, fetch_one, get_db

role_router = APIRouter(prefix="/role", tags=["admin-role"])
menu_router = APIRouter(prefix="/menu", tags=["admin-menu"])
resource_router = APIRouter(prefix="/resource", tags=["admin-resource"])
resource_category_router = APIRouter(prefix="/resourceCategory", tags=["admin-resource-category"])


# --- Role ---
@role_router.get("/listAll")
def role_list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(serialize_rows(fetch_all(db, "SELECT * FROM ums_role ORDER BY sort ASC, id ASC")))


@role_router.get("/list")
def role_list(
    keyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(5, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if keyword:
        conditions.append("(name LIKE :kw OR description LIKE :kw)")
        params["kw"] = f"%{keyword}%"
    return success(paginate(db, "ums_role", " AND ".join(conditions), params, pageNum, pageSize, "sort ASC, id ASC"))


@role_router.post("/create")
def role_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "ums_role", body)
    db.commit()
    return success(1)


@role_router.post("/update/{id}")
def role_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "ums_role", id, body)
    db.commit()
    return success(1)


@role_router.post("/delete")
def role_delete(ids: str = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    id_list = parse_ids(ids)
    execute(db, f"DELETE FROM ums_role WHERE id IN ({in_ids_sql(id_list)})")
    db.commit()
    return success(len(id_list))


@role_router.post("/updateStatus/{id}")
def role_update_status(
    id: int, status: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    update_status_by_ids(db, "ums_role", [id], "status", status)
    db.commit()
    return success(1)


@role_router.get("/listMenu/{role_id}")
def role_list_menu(role_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(
        db,
        """
        SELECT m.* FROM ums_menu m
        INNER JOIN ums_role_menu_relation rmr ON m.id = rmr.menu_id
        WHERE rmr.role_id = :role_id ORDER BY m.sort DESC, m.id ASC
        """,
        {"role_id": role_id},
    )
    return success(serialize_rows(rows))


@role_router.get("/listResource/{role_id}")
def role_list_resource(role_id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = fetch_all(
        db,
        """
        SELECT r.* FROM ums_resource r
        INNER JOIN ums_role_resource_relation rrr ON r.id = rrr.resource_id
        WHERE rrr.role_id = :role_id ORDER BY r.sort ASC, r.id ASC
        """,
        {"role_id": role_id},
    )
    return success(serialize_rows(rows))


@role_router.post("/allocMenu")
def role_alloc_menu(
    roleId: int = Query(...),
    menuIds: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    id_list = parse_ids(menuIds)
    execute(db, "DELETE FROM ums_role_menu_relation WHERE role_id = :role_id", {"role_id": roleId})
    for mid in id_list:
        execute(
            db,
            "INSERT INTO ums_role_menu_relation (role_id, menu_id) VALUES (:role_id, :menu_id)",
            {"role_id": roleId, "menu_id": mid},
        )
    db.commit()
    return success(len(id_list))


@role_router.post("/allocResource")
def role_alloc_resource(
    roleId: int = Query(...),
    resourceIds: str = Query(...),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    id_list = parse_ids(resourceIds)
    execute(db, "DELETE FROM ums_role_resource_relation WHERE role_id = :role_id", {"role_id": roleId})
    for rid in id_list:
        execute(
            db,
            "INSERT INTO ums_role_resource_relation (role_id, resource_id) VALUES (:role_id, :resource_id)",
            {"role_id": roleId, "resource_id": rid},
        )
    db.commit()
    return success(len(id_list))


# --- Menu ---
def _build_menu_tree(menus: list[dict], parent_id: int = 0) -> list[dict]:
    tree = []
    for m in menus:
        if int(m.get("parentId") or 0) == parent_id:
            node = dict(m)
            node["children"] = _build_menu_tree(menus, m["id"])
            tree.append(node)
    return tree


@menu_router.get("/treeList")
def menu_tree_list(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    rows = serialize_rows(fetch_all(db, "SELECT * FROM ums_menu ORDER BY sort DESC, id ASC"))
    return success(_build_menu_tree(rows))


@menu_router.get("/list/{parent_id}")
def menu_list(
    parent_id: int,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    return success(
        paginate(
            db,
            "ums_menu",
            "parent_id = :parent_id",
            {"parent_id": parent_id},
            pageNum,
            pageSize,
            "sort DESC, id ASC",
        )
    )


@menu_router.get("/{id}")
def menu_get(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(get_by_id(db, "ums_menu", id))


@menu_router.post("/create")
def menu_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "ums_menu", body)
    db.commit()
    return success(1)


@menu_router.post("/update/{id}")
def menu_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "ums_menu", id, body)
    db.commit()
    return success(1)


@menu_router.post("/delete/{id}")
def menu_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "ums_menu", id)
    db.commit()
    return success(1)


@menu_router.post("/updateHidden/{id}")
def menu_update_hidden(
    id: int, hidden: int = Query(...), db: Session = Depends(get_db), _: dict = Depends(get_current_admin)
):
    execute(db, "UPDATE ums_menu SET hidden = :hidden WHERE id = :id", {"hidden": hidden, "id": id})
    db.commit()
    return success(1)


# --- Resource ---
@resource_router.get("/listAll")
def resource_list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(serialize_rows(fetch_all(db, "SELECT * FROM ums_resource ORDER BY id ASC")))


@resource_router.get("/list")
def resource_list(
    categoryId: int | None = None,
    nameKeyword: str | None = None,
    urlKeyword: str | None = None,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    conditions = ["1=1"]
    params: dict = {}
    if categoryId is not None:
        conditions.append("category_id = :categoryId")
        params["categoryId"] = categoryId
    if nameKeyword:
        conditions.append("name LIKE :nameKeyword")
        params["nameKeyword"] = f"%{nameKeyword}%"
    if urlKeyword:
        conditions.append("url LIKE :urlKeyword")
        params["urlKeyword"] = f"%{urlKeyword}%"
    return success(paginate(db, "ums_resource", " AND ".join(conditions), params, pageNum, pageSize, "id ASC"))


@resource_router.post("/create")
def resource_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "ums_resource", body)
    db.commit()
    return success(1)


@resource_router.post("/update/{id}")
def resource_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "ums_resource", id, body)
    db.commit()
    return success(1)


@resource_router.post("/delete/{id}")
def resource_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "ums_resource", id)
    db.commit()
    return success(1)


# --- Resource category ---
@resource_category_router.get("/listAll")
def resource_category_list_all(db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    return success(serialize_rows(fetch_all(db, "SELECT * FROM ums_resource_category ORDER BY sort ASC, id ASC")))


@resource_category_router.post("/create")
def resource_category_create(body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    insert_from_body(db, "ums_resource_category", body)
    db.commit()
    return success(1)


@resource_category_router.post("/update/{id}")
def resource_category_update(id: int, body: dict, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    update_from_body(db, "ums_resource_category", id, body)
    db.commit()
    return success(1)


@resource_category_router.post("/delete/{id}")
def resource_category_delete(id: int, db: Session = Depends(get_db), _: dict = Depends(get_current_admin)):
    delete_by_id(db, "ums_resource_category", id)
    db.commit()
    return success(1)
