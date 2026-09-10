"""RabbitMQ consumer modules.

Consumers are imported from their defining modules so importing one consumer
does not eagerly load every worker runtime and its optional dependencies.
"""
