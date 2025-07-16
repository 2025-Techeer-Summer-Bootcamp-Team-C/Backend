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

class ChangeBgSerializer(serializers.Serializer):
    image     = serializers.CharField(required=False)     # URL
    image_file = serializers.ImageField(required=False)   # 업로드 파일
    replace   = serializers.CharField(default="white studio")
    negative  = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if not (data.get("image") or data.get("image_file")):
            raise serializers.ValidationError("image 또는 image_file 중 하나는 필수입니다.")
        # 하나만 남기도록 정리
        data["image"] = data.pop("image_file", data.get("image"))
        return data
