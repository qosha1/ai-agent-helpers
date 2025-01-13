"""
Example "golden sample" of a fully fleshed Django REST Framework ViewSet.

Includes:
- ModelViewSet (all mixin actions)
- Custom permissions
- Overridden querysets & serializers
- drf-spectacular documentation
- Custom actions & thorough docstrings
"""

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, CreateModelMixin, DestroyModelMixin

# drf-spectacular imports
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiResponse,
    OpenApiExample,
)

# Local imports: adapt these to your project
from rest_framework.viewsets import GenericViewSet

from .models import MyModel
from .serializers import MyModelSerializer, MyModelDetailedSerializer
from .permissions import IsOwnerOrReadOnly


@extend_schema_view(
    # High-level tags for grouping in the OpenAPI schema
    list=extend_schema(
        summary="Retrieve a list of MyModel objects",
        description=(
            "Returns a paginated list of MyModel objects. "
            "Filtering, ordering, and pagination can be customized in settings."
        ),
    ),
    retrieve=extend_schema(
        summary="Retrieve a specific MyModel",
        description="Returns the details of a single MyModel instance, by ID.",
    ),
    create=extend_schema(
        summary="Create a new MyModel",
        description="Endpoint to create a new MyModel instance.",
    ),
    update=extend_schema(
        summary="Update an entire MyModel",
        description="Full update of a MyModel object by ID (all fields).",
    ),
    partial_update=extend_schema(
        summary="Partial update of a MyModel",
        description="Partially update a MyModel instance (only specified fields).",
    ),
    destroy=extend_schema(
        summary="Delete a MyModel",
        description="Removes a specific MyModel instance by ID.",
    ),
)
class MyModelViewSet(CreateModelMixin, RetrieveModelMixin, ListModelMixin, UpdateModelMixin, DestroyModelMixin, GenericViewSet):
    """
    A fully-featured Django REST Framework ViewSet for MyModel.

    This ViewSet illustrates:
      - Usage of all CRUD mixin actions (list, retrieve, create, update, partial_update, destroy).
      - Override of permissions and querysets.
      - Different serializers for different actions.
      - Custom actions with drf-spectacular documentation.
    """

    # Default serializer
    serializer_class = MyModelSerializer
    # Default queryset
    queryset = MyModel.objects.all()
    # Default permission for all actions
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Optionally override the default queryset.

        Example:
          - Return all objects if the user is staff.
          - Return only objects owned by the user otherwise.
        """
        user = self.request.user
        if user.is_staff:
            return MyModel.objects.all()
        return MyModel.objects.filter(owner=user)

    def get_permissions(self):
        """
        Dynamically set permissions based on the action.

        For example:
          - 'list' and 'retrieve' => allow read for any authenticated user.
          - 'create', 'update', 'partial_update', 'destroy' => must be the object's owner.
        """
        if self.action in ["list", "retrieve"]:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
        return [p() for p in permission_classes]

    def get_serializer_class(self):
        """
        Use a more detailed serializer for 'retrieve' and 'list' actions.
        Otherwise, default to the simpler serializer.
        """
        if self.action in ["retrieve", "list"]:
            return MyModelDetailedSerializer
        return MyModelSerializer

    @extend_schema(
        summary="Perform a custom reset action",
        description=(
            "Custom action that resets some field on MyModel. "
            "This is a detail route, so it applies to one specific MyModel instance."
        ),
        parameters=[
            OpenApiParameter(
                name="pk",
                description="Primary key (ID) of the MyModel instance.",
                required=True,
                type=int,
            ),
        ],
        responses={{
            200: OpenApiResponse(
                description="Successfully performed custom reset action.",
                response=MyModelSerializer,
            ),
            400: OpenApiResponse(description="Bad request"),
        }},
        examples=[
            OpenApiExample(
                "Successful reset",
                value={{"detail": "Field has been reset."}},
            ),
        ],
    )
    @action(methods=["post"], detail=True, url_path="reset-field")
    def reset_field(self, request, pk=None):
        """
        POST /my_model/<pk>/reset-field/

        A custom detail route that manipulates a single MyModel instance
        by "resetting" one of its fields to a default value.
        """
        instance = self.get_object()
        # Example: reset a hypothetical 'status' field
        instance.status = "default"
        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Bulk update for MyModel objects",
        description=(
            "A custom action for bulk updating multiple MyModel instances at once. "
            "This is a collection (list) route."
        ),
        request={{
            "application/json": OpenApiExample(
                "Bulk request example",
                value=[
                    {{"id": 1, "status": "new_status"}},
                    {{"id": 2, "status": "another_status"}},
                ],
            ),
        }},
        responses={{
            200: OpenApiResponse(
                description="Bulk update success",
                response=MyModelSerializer(many=True),
            ),
            400: OpenApiResponse(description="Bad request"),
        }},
    )
    @action(methods=["patch"], detail=False, url_path="bulk-update")
    def bulk_update(self, request):
        """
        PATCH /my_model/bulk-update/

        Custom list route for updating multiple MyModel items at once.
        Expects JSON data in the format:
            [
              {{"id": <int>, "field": <value>, ...}},
              ...
            ]
        """
        data_list = request.data  # typically a list of dicts
        updated_instances = []

        for item in data_list:
            # Retrieve each object
            obj_id = item.get("id")
            instance = get_object_or_404(MyModel, pk=obj_id)
            # You might want to enforce ownership permission here
            self.check_object_permissions(request, instance)

            # Update instance with partial data
            serializer = self.get_serializer(instance, data=item, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            updated_instances.append(serializer.instance)

        # Return all updated instances
        response_serializer = self.get_serializer(updated_instances, many=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
