from rest_framework import serializers

class GeminiStyleURLSerializer(serializers.Serializer):
    image_url = serializers.URLField(help_text="분석할 이미지의 URL")

class GeminiStyleResultSerializer(serializers.Serializer):
    result = serializers.CharField(help_text="스타일 키워드 결과 (예: #미니멀 #스트리트 #빈티지 #캐주얼 #모던)")
