from sqlalchemy import Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import BYTEA

from util.config import config


class EncryptedString(TypeDecorator):
    impl = Text  # Default implementation
    cache_ok = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_postgresql = False

    def load_dialect_impl(self, dialect):
        self._is_postgresql = dialect.name == "postgresql"
        if dialect.name == "postgresql":
            return dialect.type_descriptor(BYTEA())
        else:
            # For SQLite and other databases (e.g. used in tests and locally), use TEXT
            return dialect.type_descriptor(Text())

    def bind_expression(self, bindparam):
        # Only use pgcrypto functions for PostgreSQL
        if self._is_postgresql:
            return func.pgp_sym_encrypt(bindparam, config.token_encrypt_secret.get_secret_value())
        # For other databases, return the value as-is (for testing)
        return bindparam

    def column_expression(self, column):
        # Only use pgcrypto functions for PostgreSQL
        if self._is_postgresql:
            return func.pgp_sym_decrypt(column, config.token_encrypt_secret.get_secret_value())
        # For other databases, return the column as-is (for testing)
        return column

    def bind_processor(self, dialect):
        if not self._is_postgresql:
            # For non-PostgreSQL databases, just return the value as-is
            def bind_process(value):
                return value
            return bind_process
        return None

    def result_processor(self, dialect, coltype):
        if not self._is_postgresql:
            # For non-PostgreSQL databases, just return the value as-is
            def result_process_plain(value):
                return value
            return result_process_plain
        else:
            # For PostgreSQL, convert decrypted bytes to string
            def result_process_decrypt(value):
                if value is None:
                    return None
                if isinstance(value, memoryview):
                    return value.tobytes().decode("utf-8")
                elif isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value) if value is not None else None
            return result_process_decrypt
