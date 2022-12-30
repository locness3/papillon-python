# importe les modules importants
from pyexpat.errors import messages
import hug
import pronotepy
import datetime
import time
import secrets
import falcon

# importe les ENT
from pronotepy.ent import *

# ajouter les CORS sur toutes les routes
@hug.response_middleware()
def CORS(request, response, resource):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.set_header(
        'Access-Control-Allow-Headers',
        'Authorization,Keep-Alive,User-Agent,'
        'If-Modified-Since,Cache-Control,Content-Type'
    )
    response.set_header(
        'Access-Control-Expose-Headers',
        'Authorization,Keep-Alive,User-Agent,'
        'If-Modified-Since,Cache-Control,Content-Type'
    )
    if request.method == 'OPTIONS':
        response.set_header('Access-Control-Max-Age', 1728000)
        response.set_header('Content-Type', 'text/plain charset=UTF-8')
        response.set_header('Content-Length', 0)
        response.status_code = hug.HTTP_204

# système de tokens
saved_clients = {}
"""
saved_clients ->
    token ->
        client -> instance de pronotepy.Client
        last_interaction -> int (provenant de time.time(), entier représentant le temps depuis la dernière intéraction avec le client)
"""
client_timeout_threshold = 300 # le temps en sec avant qu'un jeton ne soit rendu invalide

def get_client(token: str) -> tuple[str, pronotepy.Client|None]:
    """Retourne le client Pronote associé au jeton.

    Args:
        token (str): le jeton à partir duquel retrouver le client.

    Returns:
        tuple: le couple (statut, client?) associé au jeton
            str: le statut de la demande ('ok' si le client est trouvé, 'expired' si le jeton a expiré, 'notfound' si le jeton n'est pas associé à un client)
            pronotepy.Client|None: une instance de client si le token est valide, None sinon.

    """
    if token in saved_clients:
        client_dict = saved_clients[token]
        if time.time() - client_dict['last_interaction'] < client_timeout_threshold:
            client_dict['last_interaction'] = time.time()
            return 'ok', client_dict['client']
        else:
            del saved_clients[token]
            print(len(saved_clients), 'valid tokens')
            return 'expired', None
    else:
        return 'notfound', None

# requête initiale :
# un client doit faire
# token = POST /generatetoken body={url, username, password, ent}
# GET * token=token
@hug.post('/generatetoken')
def generate_token(response, body=None):
    if not body is None:
        noENT = False

        for rk in ('url', 'username', 'password', 'ent'):
            if not rk in body and rk != 'ent':
                response.status = falcon.get_http_status(400)
                return f'missing{rk}'   
            elif not rk in body and rk == 'ent':
                noENT = True 

        try:
            if noENT:
                client = pronotepy.Client(body['url'], username=body['username'], password=body['password'])
            else:
                client = pronotepy.Client(body['url'], username=body['username'], password=body['password'], ent=getattr(pronotepy.ent, body['ent']))
        except Exception as e:
            response.status = falcon.get_http_status(498)
            print(e)

            error = {
                "token": False,
                "error": str(e),
            }
            return error
        
        token = secrets.token_urlsafe(16)

        saved_clients[token] = {
            'client': client,
            'last_interaction': time.time()
        }

        print(len(saved_clients), 'valid tokens')

        # if error return error
        if client.logged_in:
            tokenArray = {
                "token": token,
                "error": False
            }
            return tokenArray
        else:
            response.status = falcon.get_http_status(498)
            error = {
                "token": False,
                "error": "loginfailed",
            }
            return error
    else:
        response.status = falcon.get_http_status(400)
        error = {
            "token": False,
            "error": "missingbody",
        }
        return error

# donne les infos sur l'user
@hug.get('/user')
def user(token, response):
    success, client = get_client(token)

    if success == 'ok':
        if client.logged_in:
            userData = {
                "name": client.info.name,
                "class": client.info.class_name,
                "establishment": client.info.establishment,
                "phone": client.info.phone,
                "profile_picture": client.info.profile_picture.url,
                "delegue": client.info.delegue
            }

            return userData
    else:
        response.status = falcon.get_http_status(498)
        return success

## renvoie l'emploi du temps
@hug.get('/timetable')
def timetable(token, dateString, response):
    dateToGet = datetime.datetime.strptime(dateString, "%Y-%m-%d")
    success, client = get_client(token)

    if success == 'ok':
        if client.logged_in:
            lessons = client.lessons(dateToGet)

            lessonsData = []
            for lesson in lessons:
                lessonData = {
                    "id": lesson.id,
                    "subject": {
                        "id": lesson.subject.id,
                        "name": lesson.subject.name,
                        "group": lesson.subject.group
                    },
                    "teacher": lesson.teacher_name,
                    "room": lesson.classroom,
                    "start": lesson.start.strftime("%Y-%m-%d %H:%M"),
                    "end": lesson.end.strftime("%Y-%m-%d %H:%M"),
                    "background_color": lesson.background_color,
                    "status": lesson.status,
                    "is_cancelled": lesson.canceled,
                    "outing": lesson.outing,
                    "detention": lesson.detention,
                    "exempted": lesson.exempted,
                    "test": lesson.test,
                    "group_name": lesson.group_name,
                    "virtual": lesson.virtual_classrooms,
                }
                lessonsData.append(lessonData)

            print(lessonsData)
            return lessonsData
    else:
        response.status = falcon.get_http_status(498)
        return success

## renvoie les devoirs
@hug.get('/homework')
def homework(token, dateFrom, dateTo, response):
    dateFrom = datetime.datetime.strptime(dateFrom, "%Y-%m-%d").date()
    dateTo = datetime.datetime.strptime(dateTo, "%Y-%m-%d").date()
    success, client = get_client(token)

    if success == 'ok':
        if client.logged_in:
            homeworks = client.homework(date_from=dateFrom, date_to=dateTo)

            homeworksData = []
            for homework in homeworks:
                files = []
                for file in homework.files:
                    files.append({
                        "id": file.id,
                        "name": file.name,
                        "url": file.url,
                        "type": file.type
                    })

                homeworkData = {
                    "id": homework.id,
                    "subject": {
                        "id": homework.subject.id,
                        "name": homework.subject.name,
                        "groups": homework.subject.groups,
                    },
                    "description": homework.description,
                    "background_color": homework.background_color,
                    "done": homework.done,
                    "date": homework.date.strftime("%Y-%m-%d %H:%M"),
                    "files": files
                }
                homeworksData.append(homeworkData)

            return homeworksData
    else:
        response.status = falcon.get_http_status(498)
        return success

## renvoie les notes
@hug.get('/grades')
def grades(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allGrades = client.current_period.grades
        gradesData = []
        for grade in allGrades:
            gradeData = {
                "id": grade.id,
                "subject": {
                    "id": grade.subject.id,
                    "name": grade.subject.name,
                    "groups": grade.subject.groups,
                },
                "date": grade.date.strftime("%Y-%m-%d %H:%M"),
                "description": grade.comment,
                "is_bonus": grade.is_bonus,
                "is_optional": grade.is_optionnal,
                "grade": {
                    "value": grade.grade,
                    "out_of": grade.out_of,
                    "coefficient": grade.coefficient,
                    "average": grade.average,
                    "max": grade.max,
                    "min": grade.min,
                }
            }

            gradesData.append(gradeData)

        averagesData = []

        allAverages = client.current_period.averages
        for average in allAverages:
            averageData = {
                "subject": {
                    "id": average.subject.id,
                    "name": average.subject.name,
                    "groups": average.subject.groups,
                },
                "average": average.student,
                "class_average": average.class_average,
                "max": average.max,
                "min": average.min,
                "out_of": average.out_of,
            }

            averagesData.append(averageData)

        gradeReturn = {
            "grades": gradesData,
            "averages": averagesData,
            "overall_average": client.current_period.overall_average,
        }

        return gradeReturn
    else:
        response.status = falcon.get_http_status(498)
        return success

## renvoie les absences
@hug.get('/absences')
def absences(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allAbsences = client.current_period.absences
        absencesData = []
        for absence in allAbsences:
            absenceData = {
                "id": absence.id,
                "from": absence.from_date.strftime("%Y-%m-%d %H:%M"),
                "to": absence.to_date.strftime("%Y-%m-%d %H:%M"),
                "justified": absence.justified,
                "hours": absence.hours,
                "reasons": absence.reasons,
            }

            absencesData.append(absenceData)

        return absencesData
    else:
        response.status = falcon.get_http_status(498)
        return success

@hug.get('/punishments')
def punishments(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allPunishments = client.current_period.punishments
        punishmentsData = []
        for punishment in allPunishments:
            homeworkDocs = []
            if punishment.homework_documents is not None:
                for homeworkDoc in punishment.homework_documents:
                    homeworkDocs.append({
                        "id": homeworkDoc.id,
                        "name": homeworkDoc.name,
                        "url": homeworkDoc.url,
                        "type": homeworkDoc.type
                    })

            circumstanceDocs = []
            if punishment.circumstance_documents is not None:
                for circumstanceDoc in punishment.circumstance_documents:
                    circumstanceDocs.append({
                        "id": circumstanceDoc.id,
                        "name": circumstanceDoc.name,
                        "url": circumstanceDoc.url,
                        "type": circumstanceDoc.type
                    })

            schedules = []
            if punishment.schedule is not None:
                for schedule in punishment.schedule:
                    schedules.append({
                        "id": schedule.id,
                        "start": schedule.start.strftime("%Y-%m-%d %H:%M"),
                        "duration": schedule.duration,
                        "end": (schedule.start + datetime.timedelta(minutes=schedule.duration)).strftime("%Y-%m-%d %H:%M"),
                    })

            punishmentData = {
                "id": punishment.id,
                "schedulable": punishment.schedulable,
                "schedule": {
                    
                },
                "date": punishment.given.strftime("%Y-%m-%d %H:%M"),
                "given_by": punishment.giver,
                "exclusion": punishment.exclusion,
                "during_lesson": punishment.during_lesson,
                "homework": {
                    "text": punishment.homework,
                    "documents": homeworkDocs,
                },
                "reason": {
                    "text": punishment.reasons,
                    "circumstances": punishment.circumstances,
                    "documents": circumstanceDocs,
                },
                "nature": punishment.nature,
                "duration": punishment.duration
            }

            punishmentsData.append(punishmentData)

        return punishmentsData
    else:
        response.status = falcon.get_http_status(498)
        return success

@hug.get('/news')
def news(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allNews = client.information_and_surveys()

        newsAllData = []
        for news in allNews:
            attachments = []
            if news.attachments is not None:
                for attachment in news.attachments:
                    attachments.append({
                        "id": attachment.id,
                        "name": attachment.name,
                        "url": attachment.url,
                        "type": attachment.type
                    })

            newsData = {
                "id": news.id,
                "title": news.title,
                "date": news.creation_date.strftime("%Y-%m-%d %H:%M"),
                "category": news.category,
                "read": news.read,
                "survey": news.survey,
                "anonymous_survey": news.anonymous_response,
                "author": news.author,
                "content": news.content,
                "attachments": attachments,
                "html_content": news._raw_content
            }

            newsAllData.append(newsData)

        return newsAllData
    else:
        response.status = falcon.get_http_status(498)
        return success

@hug.get('/discussions')
def discussions(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allDiscussions = client.discussions()

        discussionsAllData = []
        for discussion in allDiscussions:
            messages = []
            for message in discussion.messages:
                messages.append({
                    "id": message.id,
                    "content": message.content,
                    "author": message.author,
                    "date": message.date.strftime("%Y-%m-%d %H:%M"),
                    "seen": message.seen
                })

            discussionData = {
                "id": discussion.id,
                "subject": {
                    "id": discussion.subject.id,
                    "name": discussion.subject.name,
                    "groups": discussion.subject.groups,
                },
                "creator": discussion.creator,
                "date": discussion.date.strftime("%Y-%m-%d %H:%M"),
                "unread": discussion.unread,
                "closed": discussion.close,
                "messages": messages
            }

            discussionsAllData.append(discussionData)

        return discussionsAllData
    else:
        response.status = falcon.get_http_status(498)
        return success

# Renvoie les évaluations
@hug.get('/evaluations')
def evaluations(token, response):
    success, client = get_client(token)
    if success == 'ok':
        allEvaluations = client.current_period.evaluations

        evaluationsAllData = []
        for evaluation in allEvaluations:
            acquisitions = []
            if evaluation.acquisitions is not None:
                for acquisition in evaluation.acquisitions:
                    acquisitions.append({
                        "id": acquisition.id,
                        "name": acquisition.name,
                        "coefficient": acquisition.coefficient,
                        "abbreviation": acquisition.abbreviation,
                        "domain": acquisition.domain,
                        "level": acquisition.level
                    })

            evaluationData = {
                "id": evaluation.id,
                "subject": {
                    "id": evaluation.subject.id,
                    "name": evaluation.subject.name,
                    "groups": evaluation.subject.groups,
                },
                "name": evaluation.name,
                "description": evaluation.description,
                "teacher": evaluation.teacher,
                "date": evaluation.date.strftime("%Y-%m-%d %H:%M"),
                "paliers": evaluation.paliers,
                "coefficient": evaluation.coefficient,
                "acquisitions": acquisitions,
            }

            evaluationsAllData.append(evaluationData)

        return evaluationsAllData
    else:
        response.status = falcon.get_http_status(498)
        return success

def __getMealFood(meal):
    if meal is None:
        return None
    else:
        foods = []
        for food in meal:
            foods.append({
                        "name": food.name,
                        "labels": __getFoodLabels(food.labels),
                    })
        return foods

def __getFoodLabels(labels):
    if labels is None:
        return None
    else:
        foodLabels = []
        for label in labels:
            foodLabels.append({
                "id": label.id,
                "name": label.name,
                "color": label.color,
            })
        return foodLabels

@hug.get('/menu')
def menu(token, dateFrom, dateTo, response):
    dateFrom = datetime.datetime.strptime(dateFrom, "%Y-%m-%d").date()
    dateTo = datetime.datetime.strptime(dateTo, "%Y-%m-%d").date()
    success, client = get_client(token)
    if success == 'ok':
        allMenus = client.menus(date_from=dateFrom, date_to=dateTo)

        menusAllData = []
        for menu in allMenus:
            cheese = __getMealFood(menu.cheese)
            dessert = __getMealFood(menu.dessert)
            other_meal = __getMealFood(menu.other_meal)
            side_meal = __getMealFood(menu.side_meal)
            main_meal = __getMealFood(menu.main_meal)
            first_meal = __getMealFood(menu.first_meal)

            menuData = {
                "id": menu.id,
                "name": menu.name,
                "date": menu.date.strftime("%Y-%m-%d"),
                "type": {
                    "is_lunch": menu.is_lunch,
                    "is_dinner": menu.is_dinner,
                },
                "first_meal": first_meal,
                "dessert": dessert,
                "cheese": cheese,
                "other_meal": other_meal,
                "side_meal": side_meal,
                "main_meal": main_meal,
            }

            menusAllData.append(menuData)

        return menusAllData
    else:
        response.status = falcon.get_http_status(498)
        return success

@hug.get('/export/ical')
def export_ical(token, response):
    success, client = get_client(token)
    
    if success == 'ok':
        ical_url = client.export_ical()
        return ical_url
    else:
        response.status = falcon.get_http_status(498)
        return success

@hug.get('/homework/setAsDone')
def homework_setAsDone(token, dateFrom, dateTo, homeworkId, response):
    dateFrom = datetime.datetime.strptime(dateFrom, "%Y-%m-%d").date()
    dateTo = datetime.datetime.strptime(dateTo, "%Y-%m-%d").date()
    success, client = get_client(token)

    if success == 'ok':
        if client.logged_in:
            homeworks = client.homework(date_from=dateFrom, date_to=dateTo)

            incr = 0

            for homework in homeworks:
                if incr == homeworkId:
                    print(homework)
                    homework.set_done(False)

                incr += 1
    else:
        response.status = falcon.get_http_status(498)
        return success
    