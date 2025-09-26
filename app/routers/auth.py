from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from .. import schemas, crud, auth, dependencies, database

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=schemas.Token)
def login(user_data: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = crud.authenticate_user(db, user_data.login, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect login or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )

    refresh_token_db = crud.create_refresh_token_db(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_db.token,
        "token_type": "bearer",
        "user_role": user.role,
        "expires_in": auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
        token_data: schemas.RefreshTokenRequest,
        db: Session = Depends(database.get_db)
):
    db_refresh_token = crud.get_valid_refresh_token(db, token_data.refresh_token)
    if not db_refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db_refresh_token.user

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )

    new_refresh_token_db = crud.create_refresh_token_db(db, user.id)

    crud.revoke_refresh_token(db, token_data.refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token_db.token,
        "token_type": "bearer",
        "user_role": user.role,
        "expires_in": auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


@router.post("/logout")
def logout(
        token_data: schemas.RefreshTokenRequest,
        db: Session = Depends(database.get_db)
):
    crud.revoke_refresh_token(db, token_data.refresh_token)
    return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(
        current_user: dict = Depends(dependencies.get_current_user),
        db: Session = Depends(database.get_db)
):
    crud.revoke_all_user_tokens(db, current_user["user_id"])
    return {"message": "Logged out from all devices"}


@router.post("/users/manual", response_model=schemas.UserResponse)
def create_user_manual(
        user_data: schemas.UserCreateManual,
        current_user: dict = Depends(dependencies.require_superuser),
        db: Session = Depends(database.get_db)
):
    if not dependencies.can_create_user(current_user["role"], user_data.role):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        user = crud.create_user_manual(db, user_data, created_by=current_user["user_id"])
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/users/auto", response_model=schemas.UserResponse)
def create_user_auto(
        user_data: schemas.UserCreateAuto,
        current_user: dict = Depends(dependencies.require_superuser),
        db: Session = Depends(database.get_db)
):
    if not dependencies.can_create_user(current_user["role"], user_data.role):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    user, generated_password = crud.create_user_auto(db, user_data, created_by=current_user["user_id"])

    response = schemas.UserResponse.from_orm(user)
    response.generated_password = generated_password
    return response


@router.put("/users/me", response_model=schemas.UserResponse)
def update_current_user(
        user_data: schemas.UserUpdate,
        current_user: dict = Depends(dependencies.get_current_user),
        db: Session = Depends(database.get_db)
):
    try:
        updated_user = crud.update_user(db, current_user["user_id"], user_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user_by_id(
        user_id: int,
        user_data: schemas.UserUpdate,
        _current_user: dict = Depends(dependencies.require_superuser),
        db: Session = Depends(database.get_db)
):
    try:

        updated_user = crud.update_user(db, user_id, user_data)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_info(
        current_user: dict = Depends(dependencies.get_current_user),
        db: Session = Depends(database.get_db)
):
    user = crud.get_user_by_id(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
