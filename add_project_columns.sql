-- Migration script to add transcript caching columns to projects table
-- Run this SQL directly on your PostgreSQL database
-- If a column already exists, you'll get an error - that's okay, just skip that command

-- Add transcript column
ALTER TABLE projects ADD COLUMN transcript TEXT;

-- Add transcript_fetched_at column  
ALTER TABLE projects ADD COLUMN transcript_fetched_at TIMESTAMP;

-- Add video_description column
ALTER TABLE projects ADD COLUMN video_description TEXT;

