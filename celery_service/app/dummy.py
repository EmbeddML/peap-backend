from celery import Celery, signature
import celery_conf

app = Celery()
app.config_from_object(celery_conf)

result = signature('get_tweets', args=('bbudka', )).delay()

print(result.get())
