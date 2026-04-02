# Aisha Codebase Function Analysis

**Total Functions Found:** 180

## scripts/generate_icons.py
- [ ] `generate_icons`
- [ ] `_generate_with_pillow`
- [ ] `_generate_svg_icons`

## scripts/import_history.py
- [ ] `parse_chatgpt`
- [ ] `parse_claude`
- [ ] `parse_gemini`
- [ ] `parse_grok`
- [ ] `extract_memories`
- [ ] `save_to_supabase`
- [ ] `save_to_file`
- [ ] `main`

## scripts/run_tests.py
- [ ] `test`
- [ ] `test_config`
- [ ] `test_language_detector`
- [ ] `test_mood_detector`
- [ ] `test_memory_manager`
- [ ] `test_ai_brain`
- [ ] `test_telegram_bot`
- [ ] `assert_equal`
- [ ] `main`
- [ ] `check_defaults`
- [ ] `check_profile`
- [ ] `check_memories`
- [ ] `check_tasks`
- [ ] `check_english`
- [ ] `check_hindi`
- [ ] `check_motivation_mode`
- [ ] `check_bot_init`

## scripts/test_aisha.py
- [ ] `test_env_vars`
- [ ] `test_gemini`
- [ ] `test_supabase`
- [ ] `run_chat_test`
- [ ] `interactive_mode`

## src/agents/boss_aisha.py
- [ ] `__init__`
- [ ] `delegate_task`

## src/agents/dev_crew.py
- [ ] `get_llm`
- [ ] `architect`
- [ ] `dev`
- [ ] `tester`
- [ ] `reviewer`
- [ ] `architect_task`
- [ ] `write_code_task`
- [ ] `test_code_task`
- [ ] `review_code_task`
- [ ] `crew`

## src/agents/tools/execution_tools.py
- [ ] `run_python_tests`
- [ ] `check_python_syntax`

## src/agents/tools/file_tools.py
- [ ] `read_file`
- [ ] `write_file`
- [ ] `list_directory`
- [ ] `save_to_journal`

## src/agents/tools/media_tools.py
- [ ] `generate_audio`
- [ ] `generate_image`
- [ ] `sync_video`

## src/agents/tools/youtube_tools.py
- [ ] `search_youtube_trends`
- [ ] `upload_to_youtube`

## src/agents/youtube_crew.py
- [ ] `riya`
- [ ] `lexi`
- [ ] `zara`
- [ ] `aria`
- [ ] `mia`
- [ ] `sync`
- [ ] `cappy`
- [ ] `research_task`
- [ ] `crew`

## src/core/ai_router.py
- [ ] `is_cooling_down`
- [ ] `mark_failure`
- [ ] `mark_success`
- [ ] `__init__`
- [ ] `_init_clients`
- [ ] `generate`
- [ ] `_call_provider`
- [ ] `_call_gemini`
- [ ] `_call_openai`
- [ ] `_call_groq`
- [ ] `_call_xai`
- [ ] `_call_anthropic`
- [ ] `_model_name`
- [ ] `_fallback_message`

## src/core/aisha_brain.py
- [ ] `build_system_prompt`
- [ ] `__init__`
- [ ] `think`
- [ ] `_auto_extract_memory`
- [ ] `reset_session`

## src/core/autonomous_loop.py
- [ ] `start_loop`
- [ ] `__init__`
- [ ] `run_morning_checkin`
- [ ] `run_memory_consolidation`
- [ ] `monitor_health_and_fix_bugs`

## src/core/config.py
- [ ] `_get`
- [ ] `validate_required`
- [ ] `print_status`
- [ ] `mask`

## src/core/image_engine.py
- [ ] `generate_image`

## src/core/language_detector.py
- [ ] `detect_language`
- [ ] `get_response_language_instruction`

## src/core/mood_detector.py
- [ ] `detect_mood`
- [ ] `_build_result`
- [ ] `get_mood_prompt_addon`

## src/core/self_improvement.py
- [ ] `create_github_pr`
- [ ] `notify_ajay_for_approval`
- [ ] `merge_github_pr`

## src/core/video_engine.py
- [ ] `_split_script_into_scenes`
- [ ] `_get_audio_duration`
- [ ] `generate_scene_images`
- [ ] `produce_video`

## src/core/voice_engine.py
- [ ] `_generate_voice_async`
- [ ] `_generate_elevenlabs`
- [ ] `_transliterate_hinglish`
- [ ] `generate_voice`
- [ ] `cleanup_voice_file`
- [ ] `_clean_for_speech`

## src/memory/memory_manager.py
- [ ] `__init__`
- [ ] `get_profile`
- [ ] `update_mood`
- [ ] `get_top_memories`
- [ ] `get_semantic_memories`
- [ ] `_generate_embedding`
- [ ] `save_memory`
- [ ] `save_emotional_memory`
- [ ] `save_skill_memory`
- [ ] `save_episodic_memory`
- [ ] `save_conversation`
- [ ] `get_recent_conversation`
- [ ] `load_context`
- [ ] `get_today_tasks`

## src/skills/memory_skill.py
- [ ] `learn_new_rule`
- [ ] `memorize_fact`

## src/skills/pro_photo_skill.py
- [ ] `white_balance_grayworld`
- [ ] `auto_exposure`
- [ ] `enhance_vibrance`
- [ ] `sharpen_image`
- [ ] `auto_correct_photo`
- [ ] `remove_background`
- [ ] `make_curve`
- [ ] `apply_lut_1d`
- [ ] `color_grade_photo`

## src/skills/security_skill.py
- [ ] `ask_ajay_for_permission`

## src/skills/skill_registry.py
- [ ] `aisha_skill`
- [ ] `__init__`
- [ ] `_load_skills`
- [ ] `get_skill`
- [ ] `list_skills_for_ai`
- [ ] `execute_skill`
- [ ] `list_skills`

## src/skills/weather_skill.py
- [ ] `get_weather`

## src/telegram/bot.py
- [ ] `get_user_role`
- [ ] `is_admin`
- [ ] `unauthorized_response`
- [ ] `main_keyboard`
- [ ] `mood_keyboard`
- [ ] `cmd_start`
- [ ] `cmd_help`
- [ ] `cmd_imagine`
- [ ] `cmd_mood`
- [ ] `cmd_today`
- [ ] `cmd_expense`
- [ ] `cmd_goals`
- [ ] `cmd_memory`
- [ ] `cmd_reset`
- [ ] `cmd_voice`
- [ ] `cmd_journal`
- [ ] `handle_mood_callback`
- [ ] `handle_quick_action`
- [ ] `handle_voice`
- [ ] `handle_photo`
- [ ] `handle_text`
- [ ] `handle_allow_guest`
- [ ] `handle_ignore_guest`
- [ ] `handle_approve_guest_req`
- [ ] `handle_deny_guest_req`
- [ ] `handle_deploy_skill`
- [ ] `handle_skip_skill`
- [ ] `cmd_gitpull`

## src/telegram/handlers.py
- [ ] `register_commands`
- [ ] `main_keyboard`
- [ ] `mood_keyboard`
- [ ] `get_time_greeting`

## src/telegram/voice_handler.py
- [ ] `transcribe_voice_message`
- [ ] `get_voice_error_message`
