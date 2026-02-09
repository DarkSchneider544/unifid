from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
import uuid as uuid_lib

from ..models.food import FoodItem, FoodOrder, FoodOrderItem
from ..models.user import User
from ..models.enums import OrderStatus
from ..schemas.food import FoodItemCreate, FoodItemUpdate, FoodOrderCreate
from .embedding_service import EmbeddingService


class FoodService:
    """Food item and order management service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
    
    async def get_food_item_by_id(
        self,
        item_id: UUID
    ) -> Optional[FoodItem]:
        """Get food item by ID."""
        result = await self.db.execute(
            select(FoodItem).where(
                FoodItem.id == item_id,
                FoodItem.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    async def create_food_item(
        self,
        item_data: FoodItemCreate,
        created_by: User
    ) -> Tuple[Optional[FoodItem], Optional[str]]:
        """Create a new food item with embedding."""
        # Generate embedding
        text_for_embedding = self.embedding_service.prepare_food_text(
            name=item_data.name,
            description=item_data.description,
            ingredients=item_data.ingredients,
            tags=item_data.tags,
            category=item_data.category
        )
        embedding = await self.embedding_service.generate_embedding(text_for_embedding)
        
        food_item = FoodItem(
            name=item_data.name,
            description=item_data.description,
            category=item_data.category,
            price=item_data.price,
            ingredients=item_data.ingredients,
            tags=item_data.tags,
            calories=item_data.calories,
            preparation_time_minutes=item_data.preparation_time_minutes,
            image_url=item_data.image_url,
            created_by_id=created_by.id,
            embedding=embedding
        )
        
        self.db.add(food_item)
        await self.db.commit()
        await self.db.refresh(food_item)
        
        return food_item, None
    
    async def update_food_item(
        self,
        item_id: UUID,
        item_data: FoodItemUpdate
    ) -> Tuple[Optional[FoodItem], Optional[str]]:
        """Update a food item."""
        food_item = await self.get_food_item_by_id(item_id)
        if not food_item:
            return None, "Food item not found"
        
        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(food_item, field, value)
        
        # Regenerate embedding if relevant fields changed
        if any(f in update_data for f in ['name', 'description', 'ingredients', 'tags', 'category']):
            text_for_embedding = self.embedding_service.prepare_food_text(
                name=food_item.name,
                description=food_item.description,
                ingredients=food_item.ingredients,
                tags=food_item.tags,
                category=food_item.category
            )
            food_item.embedding = await self.embedding_service.generate_embedding(text_for_embedding)
        
        await self.db.commit()
        await self.db.refresh(food_item)
        
        return food_item, None
    
    async def list_food_items(
        self,
        category: Optional[str] = None,
        is_available: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[FoodItem], int]:
        """List food items with filtering."""
        query = select(FoodItem).where(FoodItem.is_active == True)
        count_query = select(func.count(FoodItem.id)).where(FoodItem.is_active == True)
        
        if category:
            query = query.where(FoodItem.category == category)
            count_query = count_query.where(FoodItem.category == category)
        
        if is_available is not None:
            query = query.where(FoodItem.is_available == is_available)
            count_query = count_query.where(FoodItem.is_available == is_available)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(FoodItem.name)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total
    
    async def get_order_by_id(
        self,
        order_id: UUID
    ) -> Optional[FoodOrder]:
        """Get food order by ID with items."""
        result = await self.db.execute(
            select(FoodOrder)
            .where(FoodOrder.id == order_id)
            .options(selectinload(FoodOrder.items))
        )
        return result.scalar_one_or_none()
    
    def generate_order_number(self) -> str:
        """Generate unique order number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = str(uuid_lib.uuid4())[:6].upper()
        return f"ORD-{timestamp}-{random_part}"
    
    async def create_order(
        self,
        order_data: FoodOrderCreate,
        user: User
    ) -> Tuple[Optional[FoodOrder], Optional[str]]:
        """Create a new food order."""
        # Validate all items exist and are available
        total_amount = Decimal("0.00")
        order_items = []
        
        for item_data in order_data.items:
            food_item = await self.get_food_item_by_id(item_data.food_item_id)
            if not food_item:
                return None, f"Food item {item_data.food_item_id} not found"
            if not food_item.is_available:
                return None, f"Food item {food_item.name} is not available"
            
            item_total = food_item.price * item_data.quantity
            total_amount += item_total
            
            order_items.append({
                "food_item": food_item,
                "quantity": item_data.quantity,
                "unit_price": food_item.price,
                "total_price": item_total,
                "special_instructions": item_data.special_instructions
            })
        
        # Create order
        order = FoodOrder(
            order_number=self.generate_order_number(),
            user_id=user.id,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            is_scheduled=order_data.is_scheduled,
            scheduled_date=order_data.scheduled_date,
            scheduled_time=order_data.scheduled_time,
            notes=order_data.notes
        )
        self.db.add(order)
        await self.db.flush()
        
        # Create order items
        for item in order_items:
            order_item = FoodOrderItem(
                order_id=order.id,
                food_item_id=item["food_item"].id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_price=item["total_price"],
                special_instructions=item["special_instructions"]
            )
            self.db.add(order_item)
        
        await self.db.commit()
        await self.db.refresh(order)
        
        # Load items
        result = await self.db.execute(
            select(FoodOrder)
            .where(FoodOrder.id == order.id)
            .options(selectinload(FoodOrder.items))
        )
        order = result.scalar_one()
        
        return order, None
    
    async def update_order_status(
        self,
        order_id: UUID,
        status: OrderStatus,
        notes: Optional[str] = None,
        cancellation_reason: Optional[str] = None
    ) -> Tuple[Optional[FoodOrder], Optional[str]]:
        """Update order status."""
        order = await self.get_order_by_id(order_id)
        if not order:
            return None, "Order not found"
        
        # Validate status transition
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PREPARING, OrderStatus.CANCELLED],
            OrderStatus.PREPARING: [OrderStatus.READY, OrderStatus.CANCELLED],
            OrderStatus.READY: [OrderStatus.DELIVERED, OrderStatus.CANCELLED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: []
        }
        
        if status not in valid_transitions.get(order.status, []):
            return None, f"Cannot transition from {order.status.value} to {status.value}"
        
        order.status = status
        
        if status == OrderStatus.DELIVERED:
            order.completed_at = datetime.now(timezone.utc)
        elif status == OrderStatus.CANCELLED:
            order.cancelled_at = datetime.now(timezone.utc)
            order.cancellation_reason = cancellation_reason
        
        await self.db.commit()
        await self.db.refresh(order)
        
        return order, None
    
    async def list_orders(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[OrderStatus] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[FoodOrder], int]:
        """List food orders with filtering."""
        query = select(FoodOrder).options(selectinload(FoodOrder.items))
        count_query = select(func.count(FoodOrder.id))
        
        if user_id:
            query = query.where(FoodOrder.user_id == user_id)
            count_query = count_query.where(FoodOrder.user_id == user_id)
        
        if status:
            query = query.where(FoodOrder.status == status)
            count_query = count_query.where(FoodOrder.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        query = query.offset((page - 1) * page_size).limit(page_size)
        query = query.order_by(FoodOrder.created_at.desc())
        
        result = await self.db.execute(query)
        orders = result.scalars().unique().all()
        
        return list(orders), total
    
    async def get_dashboard_stats(self) -> dict:
        """Get cafeteria dashboard statistics."""
        # Total orders today
        today = datetime.now(timezone.utc).date()
        today_orders = await self.db.execute(
            select(func.count(FoodOrder.id)).where(
                func.date(FoodOrder.created_at) == today
            )
        )
        
        # Orders by status
        status_counts = {}
        for status in OrderStatus:
            count_result = await self.db.execute(
                select(func.count(FoodOrder.id)).where(
                    FoodOrder.status == status,
                    func.date(FoodOrder.created_at) == today
                )
            )
            status_counts[status.value] = count_result.scalar()
        
        # Total revenue today
        revenue_result = await self.db.execute(
            select(func.sum(FoodOrder.total_amount)).where(
                FoodOrder.status == OrderStatus.DELIVERED,
                func.date(FoodOrder.created_at) == today
            )
        )
        
        return {
            "total_orders_today": today_orders.scalar(),
            "orders_by_status": status_counts,
            "revenue_today": float(revenue_result.scalar() or 0)
        }