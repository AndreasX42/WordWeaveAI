package models

// import (
// 	"time"

// 	"github.com/AndreasX42/wordweave-go/db"
// )

// type Event struct {
// 	ID          int64
// 	Name        string    `json:"name" binding:"required"`
// 	Description string    `json:"description" binding:"required"`
// 	Location    string    `json:"location" binding:"required"`
// 	DateTime    time.Time `json:"date_time" binding:"required"`
// 	UserID      int64
// }

// func (e *Event) Delete(id int64) error {
// 	query := `
// 	DELETE FROM events
// 	WHERE id = ?
// 	`
// 	stmt, err := db.DB.Prepare(query)
// 	if err != nil {
// 		return err
// 	}

// 	defer stmt.Close()

// 	_, err = stmt.Exec(id)

// 	return err
// }

// func (e *Event) Update(id int64) error {
// 	query := `
// 	UPDATE events
// 	SET name = ?, description = ?, location = ?, date_time = ?, user_id = ?
// 	WHERE id = ?
// 	`
// 	stmt, err := db.DB.Prepare(query)
// 	if err != nil {
// 		return err
// 	}

// 	defer stmt.Close()

// 	_, err = stmt.Exec(e.Name, e.Description, e.Location, e.DateTime, e.UserID, id)

// 	return err
// }

// func (e *Event) Save() error {
// 	query := `
// 	INSERT INTO events (name, description, location, date_time, user_id)
// 	VALUES (?, ?, ?, ?, ?)
// 	`
// 	stmt, err := db.DB.Prepare(query)
// 	if err != nil {
// 		return err
// 	}

// 	defer stmt.Close()

// 	result, err := stmt.Exec(e.Name, e.Description, e.Location, e.DateTime, e.UserID)
// 	if err != nil {
// 		return err
// 	}

// 	id, err := result.LastInsertId()
// 	e.ID = id

// 	return err
// }

// func GetAllEvents() ([]Event, error) {
// 	query := `
// 	SELECT * FROM events
// 	`
// 	rows, err := db.DB.Query(query)
// 	if err != nil {
// 		return nil, err
// 	}

// 	defer rows.Close()

// 	events := []Event{}
// 	for rows.Next() {
// 		var event Event
// 		err := rows.Scan(&event.ID, &event.Name, &event.Description, &event.Location, &event.DateTime, &event.UserID)
// 		if err != nil {
// 			return nil, err
// 		}
// 		events = append(events, event)
// 	}

// 	return events, nil
// }

// func GetEventByID(id int64) (*Event, error) {
// 	query := `
// 	SELECT * FROM events WHERE id = ?
// 	`
// 	row := db.DB.QueryRow(query, id)

// 	var event Event
// 	err := row.Scan(&event.ID, &event.Name, &event.Description, &event.Location, &event.DateTime, &event.UserID)
// 	if err != nil {
// 		return nil, err
// 	}

// 	return &event, nil
// }
