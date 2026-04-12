"""
Service layer for Rating business logic
"""
from typing import Optional, Dict
from django.db.models import Avg, Count
from .models import Rating
from .serializers import RatingSerializer


class RatingService:
    """Service class xử lý business logic cho Rating"""
    
    @staticmethod
    def create_rating(book_id: int, customer_id: int, rating: int, comment: str = "") -> Rating:
        """
        Tạo rating mới
        
        Args:
            book_id: ID của sách
            customer_id: ID của customer
            rating: Điểm đánh giá (1-5)
            comment: Nhận xét
            
        Returns:
            Rating object đã tạo
            
        Raises:
            ValueError: Nếu customer đã đánh giá sách này rồi
        """
        # Kiểm tra xem customer đã đánh giá sách này chưa
        if Rating.objects.filter(book_id=book_id, customer_id=customer_id).exists():
            raise ValueError("Bạn đã đánh giá sách này rồi. Vui lòng cập nhật đánh giá thay vì tạo mới.")
        
        rating_obj = Rating.objects.create(
            book_id=book_id,
            customer_id=customer_id,
            rating=rating,
            comment=comment
        )
        return rating_obj
    
    @staticmethod
    def get_ratings(book_id: Optional[int] = None, customer_id: Optional[int] = None):
        """
        Lấy danh sách ratings
        
        Args:
            book_id: Lọc theo sách (optional)
            customer_id: Lọc theo customer (optional)
            
        Returns:
            QuerySet của Rating objects
        """
        queryset = Rating.objects.all()
        
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        return queryset
    
    @staticmethod
    def get_rating_by_id(rating_id: int) -> Optional[Rating]:
        """Lấy rating theo ID"""
        try:
            return Rating.objects.get(id=rating_id)
        except Rating.DoesNotExist:
            return None
    
    @staticmethod
    def update_rating(rating_id: int, data: dict, partial: bool = False) -> Optional[Rating]:
        """
        Cập nhật rating
        
        Args:
            rating_id: ID của rating
            data: Dữ liệu cập nhật
            partial: True nếu là partial update
            
        Returns:
            Rating object đã cập nhật hoặc None
        """
        rating = RatingService.get_rating_by_id(rating_id)
        if not rating:
            return None
        
        serializer = RatingSerializer(rating, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        return serializer.save()
    
    @staticmethod
    def delete_rating(rating_id: int) -> bool:
        """
        Xóa rating
        
        Args:
            rating_id: ID của rating
            
        Returns:
            True nếu xóa thành công, False nếu không tìm thấy
        """
        rating = RatingService.get_rating_by_id(rating_id)
        if not rating:
            return False
        
        rating.delete()
        return True
    
    @staticmethod
    def get_book_rating_stats(book_id: int) -> Dict:
        """
        Lấy thống kê đánh giá cho sách
        
        Args:
            book_id: ID của sách
            
        Returns:
            Dictionary chứa thống kê
        """
        ratings = Rating.objects.filter(book_id=book_id)
        stats = ratings.aggregate(
            average_rating=Avg('rating'),
            total_ratings=Count('id')
        )
        
        # Đếm số lượng mỗi loại rating
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[f'{i}_star'] = ratings.filter(rating=i).count()
        
        return {
            'book_id': book_id,
            'average_rating': round(stats['average_rating'], 2) if stats['average_rating'] else 0,
            'total_ratings': stats['total_ratings'],
            'rating_distribution': rating_distribution
        }
