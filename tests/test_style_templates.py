"""Property-based tests for StyleTemplateManager.

This module contains property-based tests using Hypothesis to verify
the correctness of style template loading and consistency.

Feature: video-style-expansion
Property 1: 风格模板加载一致性
Validates: Requirements 1.2, 1.3, 6.1, 6.2, 6.3
"""

import pytest
from hypothesis import given, settings, strategies as st

from backend.schemas.models import VideoStyle
from backend.core.style_templates import (
    StyleTemplateManager,
    TEACHING_TEMPLATE,
    NURSERY_RHYME_TEMPLATE,
    STORYBOOK_TEMPLATE,
    RECITATION_TEMPLATE,
    CUSTOM_TEMPLATE,
)


# =============================================================================
# Unit Tests
# =============================================================================

class TestStyleTemplateManagerBasic:
    """Basic unit tests for StyleTemplateManager."""

    def test_get_template_teaching(self):
        """Test loading teaching style template."""
        template = StyleTemplateManager.get_template(VideoStyle.TEACHING)
        assert template is not None
        assert len(template) > 0
        assert template == TEACHING_TEMPLATE
        # Verify teaching-specific content
        assert "知识点讲解" in template
        assert "循序渐进" in template
        assert "互动问答" in template

    def test_get_template_nursery_rhyme(self):
        """Test loading nursery rhyme style template."""
        template = StyleTemplateManager.get_template(VideoStyle.NURSERY_RHYME)
        assert template is not None
        assert len(template) > 0
        assert template == NURSERY_RHYME_TEMPLATE
        # Verify nursery rhyme-specific content
        assert "韵律节奏" in template
        assert "重复记忆" in template
        assert "欢快" in template
        # Verify TTS limitation note
        assert "语音朗读" in template or "TTS" in template

    def test_get_template_storybook(self):
        """Test loading storybook style template."""
        template = StyleTemplateManager.get_template(VideoStyle.STORYBOOK)
        assert template is not None
        assert len(template) > 0
        assert template == STORYBOOK_TEMPLATE
        # Verify storybook-specific content
        assert "故事情节" in template
        assert "角色对话" in template
        assert "情感起伏" in template

    def test_get_template_recitation(self):
        """Test loading recitation style template."""
        template = StyleTemplateManager.get_template(VideoStyle.RECITATION)
        assert template is not None
        assert len(template) > 0
        assert template == RECITATION_TEMPLATE
        # Verify recitation-specific content
        assert "情感表达" in template
        assert "节奏" in template
        assert "意境" in template

    def test_get_template_custom(self):
        """Test loading custom style template."""
        template = StyleTemplateManager.get_template(VideoStyle.CUSTOM)
        assert template is not None
        assert len(template) > 0
        assert template == CUSTOM_TEMPLATE
        # Verify custom style placeholder
        assert "{custom_style_description}" in template

    def test_get_all_styles(self):
        """Test getting all available styles."""
        styles = StyleTemplateManager.get_all_styles()
        assert len(styles) == 5
        
        # Verify all expected styles are present
        style_ids = [s["id"] for s in styles]
        assert "teaching" in style_ids
        assert "nursery_rhyme" in style_ids
        assert "storybook" in style_ids
        assert "recitation" in style_ids
        assert "custom" in style_ids
        
        # Verify each style has required fields
        for style in styles:
            assert "id" in style
            assert "name" in style
            assert "description" in style
            assert "icon" in style

    def test_get_style_by_id_valid(self):
        """Test getting style info by valid ID."""
        style = StyleTemplateManager.get_style_by_id("teaching")
        assert style is not None
        assert style["id"] == "teaching"
        assert style["name"] == "教学"

    def test_get_style_by_id_invalid(self):
        """Test getting style info by invalid ID."""
        style = StyleTemplateManager.get_style_by_id("nonexistent")
        assert style is None

    def test_is_valid_style_valid(self):
        """Test style validation with valid IDs."""
        assert StyleTemplateManager.is_valid_style("teaching") is True
        assert StyleTemplateManager.is_valid_style("nursery_rhyme") is True
        assert StyleTemplateManager.is_valid_style("storybook") is True
        assert StyleTemplateManager.is_valid_style("recitation") is True
        assert StyleTemplateManager.is_valid_style("custom") is True

    def test_is_valid_style_invalid(self):
        """Test style validation with invalid IDs."""
        assert StyleTemplateManager.is_valid_style("nonexistent") is False
        assert StyleTemplateManager.is_valid_style("") is False
        assert StyleTemplateManager.is_valid_style("TEACHING") is False  # Case sensitive


class TestTemplateContent:
    """Tests for template content requirements."""

    def test_all_templates_have_required_placeholders(self):
        """Test that all templates have required format placeholders."""
        required_placeholders = ["{topic}", "{target_audience}", "{key_points}"]
        
        for style in VideoStyle:
            template = StyleTemplateManager.get_template(style)
            for placeholder in required_placeholders:
                assert placeholder in template, (
                    f"Template for {style.value} missing placeholder {placeholder}"
                )

    def test_all_templates_have_json_output_format(self):
        """Test that all templates specify JSON output format."""
        for style in VideoStyle:
            template = StyleTemplateManager.get_template(style)
            assert "JSON" in template or "json" in template, (
                f"Template for {style.value} missing JSON output format specification"
            )

    def test_all_templates_have_audio_params_section(self):
        """Test that all templates include audio_params in output format."""
        for style in VideoStyle:
            template = StyleTemplateManager.get_template(style)
            assert "audio_params" in template, (
                f"Template for {style.value} missing audio_params in output format"
            )


# =============================================================================
# Property-Based Tests
# =============================================================================

class TestStyleTemplateLoadingConsistency:
    """Property-based tests for style template loading consistency.
    
    Feature: video-style-expansion, Property 1: 风格模板加载一致性
    Validates: Requirements 1.2, 1.3, 6.1, 6.2, 6.3
    """

    @given(style=st.sampled_from(list(VideoStyle)))
    @settings(max_examples=100)
    def test_style_template_loading_consistency(self, style: VideoStyle):
        """For any preset style, loading the template multiple times returns identical content.
        
        Property 1: 风格模板加载一致性
        Validates: Requirements 1.2, 1.3, 6.1, 6.2, 6.3
        """
        # Load template twice
        template1 = StyleTemplateManager.get_template(style)
        template2 = StyleTemplateManager.get_template(style)
        
        # Templates should be identical
        assert template1 == template2, (
            f"Template for {style.value} is not consistent across loads"
        )
        
        # Template should not be empty
        assert template1 is not None
        assert len(template1) > 0

    @given(style=st.sampled_from(list(VideoStyle)))
    @settings(max_examples=100)
    def test_template_has_required_structure(self, style: VideoStyle):
        """For any style, the template must have required structural elements.
        
        Property 1: 风格模板加载一致性 (structural consistency)
        Validates: Requirements 6.1, 6.2, 6.3
        """
        template = StyleTemplateManager.get_template(style)
        
        # All templates must have these elements
        assert "{topic}" in template, f"Template for {style.value} missing {{topic}}"
        assert "{target_audience}" in template, f"Template for {style.value} missing {{target_audience}}"
        assert "{key_points}" in template, f"Template for {style.value} missing {{key_points}}"
        
        # All templates must specify output format
        assert "scenes" in template.lower(), f"Template for {style.value} missing scenes in output"

    @given(style_id=st.sampled_from(["teaching", "nursery_rhyme", "storybook", "recitation", "custom"]))
    @settings(max_examples=100)
    def test_style_info_consistency(self, style_id: str):
        """For any valid style ID, get_style_by_id returns consistent info.
        
        Property 1: 风格模板加载一致性 (style info consistency)
        Validates: Requirements 1.2, 1.3
        """
        info1 = StyleTemplateManager.get_style_by_id(style_id)
        info2 = StyleTemplateManager.get_style_by_id(style_id)
        
        assert info1 == info2, f"Style info for {style_id} is not consistent"
        assert info1 is not None
        assert "id" in info1
        assert "name" in info1
        assert "description" in info1

    @given(style=st.sampled_from(list(VideoStyle)))
    @settings(max_examples=100)
    def test_style_enum_matches_style_info(self, style: VideoStyle):
        """For any VideoStyle enum, there must be a matching style info entry.
        
        Property 1: 风格模板加载一致性 (enum-info mapping)
        Validates: Requirements 1.2, 6.1
        """
        style_info = StyleTemplateManager.get_style_by_id(style.value)
        assert style_info is not None, f"No style info for VideoStyle.{style.name}"
        assert style_info["id"] == style.value


class TestCustomStyleTemplate:
    """Tests specific to custom style template.
    
    Validates: Requirements 1.3, 2.5
    """

    def test_custom_template_has_description_placeholder(self):
        """Custom template must have placeholder for user description."""
        template = StyleTemplateManager.get_template(VideoStyle.CUSTOM)
        assert "{custom_style_description}" in template

    def test_custom_template_can_be_formatted(self):
        """Custom template can be formatted with user description."""
        template = StyleTemplateManager.get_template(VideoStyle.CUSTOM)
        
        # Should be able to format with custom description
        formatted = template.format(
            custom_style_description="温馨治愈的风格",
            topic="测试主题",
            target_audience="3-6岁儿童",
            key_points="测试要点",
            characters_section=""
        )
        
        assert "温馨治愈的风格" in formatted
        assert "{custom_style_description}" not in formatted


class TestGetAllStylesImmutability:
    """Tests for get_all_styles returning independent copies."""

    def test_get_all_styles_returns_copy(self):
        """get_all_styles should return a copy, not the original list."""
        styles1 = StyleTemplateManager.get_all_styles()
        styles2 = StyleTemplateManager.get_all_styles()
        
        # Should be equal but not the same object
        assert styles1 == styles2
        assert styles1 is not styles2
        
        # Modifying one should not affect the other
        styles1.append({"id": "test", "name": "Test"})
        styles3 = StyleTemplateManager.get_all_styles()
        assert len(styles3) == 5  # Original length

    def test_get_style_by_id_returns_copy(self):
        """get_style_by_id should return a copy, not the original dict."""
        style1 = StyleTemplateManager.get_style_by_id("teaching")
        style2 = StyleTemplateManager.get_style_by_id("teaching")
        
        # Should be equal but not the same object
        assert style1 == style2
        assert style1 is not style2
        
        # Modifying one should not affect the other
        style1["name"] = "Modified"
        style3 = StyleTemplateManager.get_style_by_id("teaching")
        assert style3["name"] == "教学"  # Original value
