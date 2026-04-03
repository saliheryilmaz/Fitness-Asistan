from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, {})

@register.filter
def last_item_date(history):
    if history:
        return history[-1]['date']
    return ''
