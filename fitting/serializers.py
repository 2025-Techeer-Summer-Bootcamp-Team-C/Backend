from rest_framework import serializers

class VTORequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField()
    outfit_image = serializers.ImageField()

    category = serializers.CharField(max_length=20)
    detail   = serializers.CharField(max_length=20)
    fit      = serializers.CharField(max_length=20)
    length   = serializers.CharField(max_length=20)

class GenerateVTORequestSerializer(serializers.Serializer):
    person_image_id = serializers.CharField(help_text="사람 이미지 ID")
    outfit_image_id = serializers.CharField(help_text="옷 이미지 ID")

class GenerateVTOProductRequestSerializer(serializers.Serializer):
    person_image_url  = serializers.URLField()
    outfit_image_url  = serializers.URLField()
    category = serializers.CharField()

class VTOTestRequestSerializer(serializers.Serializer):
    person_image = serializers.ImageField()
    outfit_image = serializers.ImageField()
