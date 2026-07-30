from rest_framework import serializers

from .models import Variante


class VarianteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Variante
        fields = "__all__"

    def validate(self, data):

        if data["precio_menudeo"] < data["costo"]:
            raise serializers.ValidationError(
                "El precio menudeo no puede ser menor al costo."
            )

        if data["precio_mayoreo"] < data["costo"]:
            raise serializers.ValidationError(
                "El precio mayoreo no puede ser menor al costo."
            )

        return data