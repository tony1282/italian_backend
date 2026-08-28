from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):

    page_size = 50

    page_size_query_param = "page_size"

    max_page_size = 200

    def get_paginated_response(self, data):

        return Response(
            {
                "success": True,
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "data": data,
            }
        )

    def get_paginated_response_schema(self, schema):

        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "count":   {"type": "integer"},
                "next":    {"type": "string", "nullable": True},
                "previous":{"type": "string", "nullable": True},
                "data":    schema,
            },
        }
