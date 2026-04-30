# Additional CRUD endpoints for masters - to be added to app.py before "if __name__"

# Cost Center CRUD endpoints
@app.get("/api/cost-centers/{cost_center_id}")
async def get_cost_center(cost_center_id: int):
    """Get cost center details."""
    try:
        cc = db.get_cost_center(cost_center_id)
        if not cc:
            raise HTTPException(status_code=404, detail="Cost center not found")

        return {
            "id": cc.id,
            "name": cc.name,
            "parent_id": cc.parent_id,
            "category": cc.category,
            "is_active": cc.is_active,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/cost-centers/{cost_center_id}")
async def update_cost_center(cost_center_id: int, cost_center: CostCenterCreate):
    """Update an existing cost center."""
    try:
        with db.session() as session:
            from .models import CostCenter
            existing = session.get(CostCenter, cost_center_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Cost center not found")

            existing.name = cost_center.name
            existing.parent_id = cost_center.parent_id
            existing.category = cost_center.category
            session.flush()

            return {
                "id": existing.id,
                "name": existing.name,
                "parent_id": existing.parent_id,
                "category": existing.category,
                "message": f"Cost center '{existing.name}' updated successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cost-centers/{cost_center_id}")
async def delete_cost_center(cost_center_id: int):
    """Delete a cost center."""
    try:
        with db.session() as session:
            from .models import CostCenter
            cc = session.get(CostCenter, cost_center_id)
            if not cc:
                raise HTTPException(status_code=404, detail="Cost center not found")

            name = cc.name
            cc.is_active = False
            session.flush()

            return {
                "message": f"Cost center '{name}' deactivated successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Currency CRUD endpoints
@app.get("/api/currencies/{currency_id}")
async def get_currency(currency_id: int):
    """Get currency details."""
    try:
        currency = db.get_currency(currency_id)
        if not currency:
            raise HTTPException(status_code=404, detail="Currency not found")

        return {
            "id": currency.id,
            "code": currency.code,
            "symbol": currency.symbol,
            "name": currency.name,
            "decimal_places": currency.decimal_places,
            "is_base": currency.is_base,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/currencies/{currency_id}")
async def update_currency(currency_id: int, currency: CurrencyCreate):
    """Update an existing currency."""
    try:
        with db.session() as session:
            from .models import Currency
            existing = session.get(Currency, currency_id)
            if not existing:
                raise HTTPException(status_code=404, detail="Currency not found")

            existing.code = currency.code
            existing.symbol = currency.symbol
            existing.name = currency.name
            existing.decimal_places = currency.decimal_places
            existing.is_base = currency.is_base
            session.flush()

            return {
                "id": existing.id,
                "code": existing.code,
                "symbol": existing.symbol,
                "name": existing.name,
                "message": f"Currency '{existing.code}' updated successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/currencies/{currency_id}")
async def delete_currency(currency_id: int):
    """Delete a currency."""
    try:
        with db.session() as session:
            from .models import Currency
            currency = session.get(Currency, currency_id)
            if not currency:
                raise HTTPException(status_code=404, detail="Currency not found")

            if currency.is_base:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete base currency"
                )

            code = currency.code
            session.delete(currency)
            session.flush()

            return {
                "message": f"Currency '{code}' deleted successfully"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
