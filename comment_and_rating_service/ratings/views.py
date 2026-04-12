from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import Avg, Count
from .models import Rating
from .serializers import RatingSerializer


class RatingViewSet(viewsets.ModelViewSet):
    """
    ViewSet cho Rating API
    Cung cấp các endpoint: list, create, retrieve, update, destroy
    """
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    
    def list(self, request, *args, **kwargs):
        """GET /ratings/ - Lấy danh sách đánh giá"""
        book_id = request.query_params.get('book_id')
        customer_id = request.query_params.get('customer_id')
        queryset = self.filter_queryset(self.get_queryset())
        
        if book_id:
            queryset = queryset.filter(book_id=book_id)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """POST /ratings/ - Thêm đánh giá mới"""
        # Kiểm tra xem customer đã đánh giá sách này chưa
        book_id = request.data.get('book_id')
        customer_id = request.data.get('customer_id')
        
        if Rating.objects.filter(book_id=book_id, customer_id=customer_id).exists():
            return Response(
                {'error': 'Bạn đã đánh giá sách này rồi. Vui lòng cập nhật đánh giá thay vì tạo mới.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """GET /ratings/{id}/ - Lấy thông tin chi tiết đánh giá"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """PUT /ratings/{id}/ - Cập nhật đánh giá"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """DELETE /ratings/{id}/ - Xóa đánh giá"""
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def book_stats(self, request):
        """GET /ratings/book_stats/?book_id=X - Lấy thống kê đánh giá cho sách"""
        book_id = request.query_params.get('book_id')
        if not book_id:
            return Response(
                {'error': 'book_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ratings = Rating.objects.filter(book_id=book_id)
        stats = ratings.aggregate(
            average_rating=Avg('rating'),
            total_ratings=Count('id')
        )
        
        # Đếm số lượng mỗi loại rating
        rating_distribution = {}
        for i in range(1, 6):
            rating_distribution[f'{i}_star'] = ratings.filter(rating=i).count()
        
        return Response({
            'book_id': book_id,
            'average_rating': round(stats['average_rating'], 2) if stats['average_rating'] else 0,
            'total_ratings': stats['total_ratings'],
            'rating_distribution': rating_distribution
        })
