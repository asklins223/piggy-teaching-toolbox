-- MySQL initialization script
-- This runs automatically when the container starts for the first time

-- Set character set
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Create database if not exists (usually already created by MYSQL_DATABASE env)
CREATE DATABASE IF NOT EXISTS video_generator
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE video_generator;

-- Grant privileges
GRANT ALL PRIVILEGES ON video_generator.* TO 'video_user'@'%';
FLUSH PRIVILEGES;
