package routes

// import (
// 	"net/http"
// 	"strconv"

// 	"github.com/AndreasX42/wordweave-go/models"
// 	"github.com/gin-gonic/gin"
// )

// func getEvents(c *gin.Context) {
// 	events, err := models.GetAllEvents()
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not get events"})
// 		return
// 	}

// 	c.JSON(http.StatusOK, events)
// }

// func createEvent(c *gin.Context) {
// 	var event models.Event
// 	err := c.ShouldBindJSON(&event)

// 	if err != nil {
// 		c.JSON(http.StatusBadRequest, gin.H{"message": "Could not parse request"})
// 		return
// 	}

// 	event.UserID = c.GetInt64("userID")
// 	err = event.Save()

// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not create event"})
// 		return
// 	}

// 	c.JSON(http.StatusCreated, gin.H{"message": "Event created!", "event": event})

// }

// func getEvent(c *gin.Context) {
// 	eventId, err := strconv.ParseInt(c.Param("id"), 10, 64)
// 	if err != nil {
// 		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid event ID"})
// 		return
// 	}

// 	event, err := models.GetEventByID(eventId)
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not get event"})
// 		return
// 	}

// 	c.JSON(http.StatusOK, event)
// }

// func updateEvent(c *gin.Context) {
// 	eventId, err := strconv.ParseInt(c.Param("id"), 10, 64)
// 	if err != nil {
// 		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid event ID"})
// 		return
// 	}

// 	event, err := models.GetEventByID(eventId)
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not get event"})
// 		return
// 	}

// 	if event.UserID != c.GetInt64("userID") {
// 		c.JSON(http.StatusForbidden, gin.H{"message": "You are not authorized to update this event"})
// 		return
// 	}

// 	var updatedEvent models.Event
// 	err = c.ShouldBindJSON(&updatedEvent)
// 	if err != nil {
// 		c.JSON(http.StatusBadRequest, gin.H{"message": "Could not parse request"})
// 		return
// 	}

// 	updatedEvent.ID = eventId
// 	err = updatedEvent.Update(eventId)
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not update event"})
// 		return
// 	}

// 	c.JSON(http.StatusOK, gin.H{"message": "Event updated!", "event": updatedEvent})

// }

// func deleteEvent(c *gin.Context) {
// 	eventId, err := strconv.ParseInt(c.Param("id"), 10, 64)
// 	if err != nil {
// 		c.JSON(http.StatusBadRequest, gin.H{"message": "Invalid event ID"})
// 		return
// 	}

// 	event, err := models.GetEventByID(eventId)
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not get event"})
// 		return
// 	}

// 	if event.UserID != c.GetInt64("userID") {
// 		c.JSON(http.StatusForbidden, gin.H{"message": "You are not authorized to delete this event"})
// 		return
// 	}

// 	err = event.Delete(eventId)
// 	if err != nil {
// 		c.JSON(http.StatusInternalServerError, gin.H{"message": "Could not delete event"})
// 		return
// 	}

// 	c.JSON(http.StatusOK, gin.H{"message": "Event deleted!"})
// }
