CREATE TABLE IF NOT EXISTS persona (
    id INT PRIMARY KEY DEFAULT 1,
    raw_text TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT single_row CHECK (id = 1)
);
