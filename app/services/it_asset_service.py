from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone

from ..models.it_asset import ITAsset, ITAssetAssignment
from ..models.user import User
from ..models.enums import AssetStatus, AssetType
from ..schemas.it_asset import ITAssetCreate, ITAssetUpdate
from .embedding_service import EmbeddingService


class ITAssetService:
    """IT Asset management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
    
    async def get_asset_by_id(
        self,
        asset_id: UUID
    ) -> Optional[ITAsset]:
        """Get asset by ID."""
        result = await self.db.execute(
            select(ITAsset).where(ITAsset.id == asset_id)
        )
        return result.scalar_one_or_none()
    
    async def get_asset_by_asset_id(
        self,
        asset_id: str
    ) -> Optional[ITAsset]:
        """Get asset by asset_id."""
        result = await self.db.execute(
            select(ITAsset).where(ITAsset.asset_id == asset_id)
        )
        return result.scalar_one_or_none()
    
    async def create_asset(
        self,
        asset_data: ITAssetCreate
    ) -> Tuple[Optional[ITAsset], Optional[str]]:
        """Create a new IT asset with auto-generated asset_code."""
        # Generate asset_code based on asset_type (e.g., LAP-0001, MON-0001)
        prefix_map = {
            AssetType.LAPTOP: "LAP",
            AssetType.DESKTOP: "DSK",
            AssetType.MONITOR: "MON",
            AssetType.KEYBOARD: "KBD",
            AssetType.MOUSE: "MOU",
            AssetType.HEADSET: "HDS",
            AssetType.WEBCAM: "WBC",
            AssetType.DOCKING_STATION: "DOC",
            AssetType.MOBILE_PHONE: "MOB",
            AssetType.TABLET: "TAB",
            AssetType.PRINTER: "PRT",
            AssetType.SCANNER: "SCN",
            AssetType.OTHER: "OTH",
        }
        prefix = prefix_map.get(asset_data.asset_type, "AST")
        
        # Get next sequence number for this type
        result = await self.db.execute(
            select(func.count(ITAsset.id)).where(
                ITAsset.asset_code.like(f"{prefix}-%")
            )
        )
        count = result.scalar() or 0
        asset_code = f"{prefix}-{count + 1:04d}"
        
        # Check for duplicate serial number
        if asset_data.serial_number:
            result = await self.db.execute(
                select(ITAsset).where(ITAsset.serial_number == asset_data.serial_number)
            )
            if result.scalar_one_or_none():
                return None, "Serial number already exists"
        
        # Generate embedding
        text_for_embedding = self.embedding_service.prepare_asset_text(
            name=asset_data.name,
            description=asset_data.description,
            specifications=asset_data.specifications,
            vendor=asset_data.vendor,
            tags=asset_data.tags
        )
        embedding = await self.embedding_service.generate_embedding(text_for_embedding)
        
        asset = ITAsset(
            asset_code=asset_code,
            name=asset_data.name,
            asset_type=asset_data.asset_type,
            description=asset_data.description,
            vendor=asset_data.vendor,
            model=asset_data.model,
            serial_number=asset_data.serial_number,
            specifications=asset_data.specifications,
            tags=asset_data.tags,
            purchase_date=asset_data.purchase_date,
            purchase_price=asset_data.purchase_price,
            warranty_expiry=asset_data.warranty_expiry,
            location=asset_data.location,
            notes=asset_data.notes,
            embedding=embedding
        )
        
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        
        return asset, None
    
    async def update_asset(
        self,
        asset_uuid: UUID,
        asset_data: ITAssetUpdate
    ) -> Tuple[Optional[ITAsset], Optional[str]]:
        """Update an IT asset."""
        asset = await self.get_asset_by_id(asset_uuid)
        if not asset:
            return None, "Asset not found"
        
        update_data = asset_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(asset, field, value)
        
        # Regenerate embedding if relevant fields changed
        if any(f in update_data for f in ['name', 'description', 'specifications', 'vendor', 'tags']):
            text_for_embedding = self.embedding_service.prepare_asset_text(
                name=asset.name,
                description=asset.description,
                specifications=asset.specifications,
                vendor=asset.vendor,
                tags=asset.tags
            )
            asset.embedding = await self.embedding_service.generate_embedding(text_for_embedding)
        
        await self.db.commit()
        await self.db.refresh(asset)
        
        return asset, None
    
    async def assign_asset(
        self,
        asset_uuid: UUID,
        user_id: UUID,
        assigned_by: User,
        notes: Optional[str] = None
    ) -> Tuple[Optional[ITAssetAssignment], Optional[str]]:
        """Assign an asset to a user."""
        asset = await self.get_asset_by_id(asset_uuid)
        if not asset:
            return None, "Asset not found"
        
        if asset.status != AssetStatus.AVAILABLE:
            return None, f"Asset is not available (current status: {asset.status.value})"
        
        # Get user_code from user_id
        from ..models.user import User as UserModel
        user_result = await self.db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        target_user = user_result.scalar_one_or_none()
        if not target_user:
            return None, "User not found"
        
        # Create assignment
        assignment = ITAssetAssignment(
            asset_id=asset_uuid,
            user_code=target_user.user_code,
            assigned_by_code=assigned_by.user_code,
            assigned_at=datetime.now(timezone.utc),
            is_active=True,
            notes=notes
        )
        self.db.add(assignment)
        
        # Update asset status
        asset.status = AssetStatus.ASSIGNED
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment, None
    
    async def return_asset(
        self,
        assignment_id: UUID,
        notes: Optional[str] = None
    ) -> Tuple[Optional[ITAssetAssignment], Optional[str]]:
        """Return an assigned asset."""
        result = await self.db.execute(
            select(ITAssetAssignment).where(
                ITAssetAssignment.id == assignment_id,
                ITAssetAssignment.is_active == True
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return None, "Active assignment not found"
        
        assignment.returned_at = datetime.now(timezone.utc)
        assignment.is_active = False
        if notes:
            assignment.notes = (assignment.notes or "") + f" | Return: {notes}"
        
        # Update asset status
        asset = await self.get_asset_by_id(assignment.asset_id)
        if asset:
            asset.status = AssetStatus.AVAILABLE
        
        await self.db.commit()
        await self.db.refresh(assignment)
        
        return assignment, None
    
    async def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        status: Optional[AssetStatus] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[ITAsset], int]:
        """List IT assets with filtering."""
        query = select(ITAsset)
        count_query = select(func.count(ITAsset.id))
        
        if asset_type:
            query = query.where(ITAsset.asset_type == asset_type)
            count_query = count_query.where(ITAsset.asset_type == asset_type)
        
        if status:
            query = query.where(ITAsset.status == status)
            count_query = count_query.where(ITAsset.status == status)
        
        if is_active is not None:
            query = query.where(ITAsset.is_active == is_active)
            count_query = count_query.where(ITAsset.is_active == is_active)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(ITAsset.created_at.desc())
        
        result = await self.db.execute(query)
        assets = result.scalars().all()
        
        return list(assets), total
    
    async def get_user_assignments(
        self,
        user_id: UUID,
        active_only: bool = True
    ) -> List[ITAssetAssignment]:
        """Get all asset assignments for a user."""
        # Get user_code from user_id
        from ..models.user import User
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return []
        
        query = select(ITAssetAssignment).where(
            ITAssetAssignment.user_code == user.user_code
        ).options(selectinload(ITAssetAssignment.asset))
        
        if active_only:
            query = query.where(ITAssetAssignment.is_active == True)
        
        query = query.order_by(ITAssetAssignment.assigned_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())