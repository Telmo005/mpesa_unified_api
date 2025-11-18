-- Executa isto no SQL Editor do teu Supabase Dashboard
CREATE TABLE IF NOT EXISTS mpesa_transactions (
    id BIGSERIAL PRIMARY KEY,

    -- Referências
    transaction_reference TEXT NOT NULL,
    third_party_reference TEXT UNIQUE NOT NULL,

    -- IDs M-Pesa
    mpesa_transaction_id TEXT,
    mpesa_conversation_id TEXT,

    -- Dados da transação
    customer_msisdn TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    service_provider_code TEXT DEFAULT '900579',

    -- Resposta M-Pesa
    response_code TEXT NOT NULL,
    response_description TEXT NOT NULL,

    -- Status e metadados
    status TEXT DEFAULT 'pending',
    api_key_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes para performance
    CONSTRAINT unique_third_party_ref UNIQUE (third_party_reference)
);

-- Indexes para buscas rápidas
CREATE INDEX IF NOT EXISTS idx_transaction_ref ON mpesa_transactions(transaction_reference);
CREATE INDEX IF NOT EXISTS idx_mpesa_tx_id ON mpesa_transactions(mpesa_transaction_id);
CREATE INDEX IF NOT EXISTS idx_created_at ON mpesa_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_status ON mpesa_transactions(status);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_mpesa_transactions_updated_at
    BEFORE UPDATE ON mpesa_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- Execute no SQL Editor do Supabase:
ALTER TABLE mpesa_transactions
DROP CONSTRAINT IF EXISTS unique_third_party_ref;

-- Mude a coluna para permitir duplicatas:
ALTER TABLE mpesa_transactions
ALTER COLUMN third_party_reference DROP NOT NULL;

ALTER TABLE mpesa_transactions
ADD COLUMN transaction_type TEXT DEFAULT 'C2B';

ALTER TABLE mpesa_transactions ALTER COLUMN amount DROP NOT NULL;