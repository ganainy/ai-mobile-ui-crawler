-- Migration: 011_add_session_path.sql
-- Description: Add session_path column to runs table
-- Created: 2026-01-13

ALTER TABLE runs ADD COLUMN session_path TEXT;
