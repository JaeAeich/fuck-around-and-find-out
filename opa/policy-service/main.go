package main

import (
	"archive/tar"
	"bytes"
	"compress/gzip"
	"database/sql"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	_ "github.com/lib/pq"
)

// App holds the database connection
type App struct {
	DB *sql.DB
}

// Policy represents the structure of a policy in our DB
type Policy struct {
	ID        int       `json:"id"`
	Name      string    `json:"name"`
	RegoCode  string    `json:"rego_code"`
	CreatedAt time.Time `json:"created_at"`
}

func main() {
	// Database connection string
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		getEnv("DB_HOST", "postgres"),
		5432,
		getEnv("DB_USER", "admin"),
		getEnv("DB_PASSWORD", "secret"),
		getEnv("DB_DATABASE", "policies_db"),
	)

	// Connect to the database
	db, err := sql.Open("postgres", connStr)
	if err != nil {
		log.Fatalf("Error connecting to database: %v", err)
	}
	defer db.Close()

	// Wait for the DB to be ready
	err = db.Ping()
	if err != nil {
		log.Fatalf("Could not ping database: %v", err)
	}
	log.Println("Successfully connected to the database.")

	app := &App{DB: db}
	router := mux.NewRouter()

	// API endpoint to add a new policy
	router.HandleFunc("/policies", app.createPolicyHandler).Methods("POST")
	// Endpoint to serve the OPA bundle
	router.HandleFunc("/policies.tar.gz", app.getBundleHandler).Methods("GET")

	log.Println("Policy service listening on :8080")
	log.Fatal(http.ListenAndServe(":8080", router))
}

// createPolicyHandler handles adding a new policy to the database.
func (a *App) createPolicyHandler(w http.ResponseWriter, r *http.Request) {
	var p Policy
	decoder := json.NewDecoder(r.Body)
	if err := decoder.Decode(&p); err != nil {
		http.Error(w, "Invalid request payload", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()

	// Insert into database
	err := a.DB.QueryRow(
		"INSERT INTO policies(name, rego_code) VALUES($1, $2) RETURNING id, created_at",
		p.Name, p.RegoCode).Scan(&p.ID, &p.CreatedAt)

	if err != nil {
		log.Printf("Error inserting policy: %v", err)
		http.Error(w, "Error creating policy", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(p)
}

// getBundleHandler queries the DB and creates a gzipped tarball bundle.
func (a *App) getBundleHandler(w http.ResponseWriter, r *http.Request) {
	rows, err := a.DB.Query("SELECT name, rego_code FROM policies")
	if err != nil {
		log.Printf("Error querying policies for bundle: %v", err)
		http.Error(w, "Could not retrieve policies", http.StatusInternalServerError)
		return
	}
	defer rows.Close()

	// Create a buffer to write our tarball to.
	buf := new(bytes.Buffer)
	gw := gzip.NewWriter(buf)
	tw := tar.NewWriter(gw)

	// Create a manifest file
	manifest := `{
		"roots": [""]
	}`
	hdr := &tar.Header{
		Name: ".manifest",
		Mode: 0644,
		Size: int64(len(manifest)),
	}
	if err := tw.WriteHeader(hdr); err != nil {
		log.Printf("Error writing manifest header: %v", err)
		http.Error(w, "Error creating bundle", http.StatusInternalServerError)
		return
	}
	if _, err := tw.Write([]byte(manifest)); err != nil {
		log.Printf("Error writing manifest body: %v", err)
		http.Error(w, "Error creating bundle", http.StatusInternalServerError)
		return
	}


	// Add policy files to the tarball
	for rows.Next() {
		var name, regoCode string
		if err := rows.Scan(&name, &regoCode); err != nil {
			log.Printf("Error scanning policy row: %v", err)
			continue
		}
		
		// Each policy becomes a separate .rego file in the bundle
		hdr := &tar.Header{
			Name: fmt.Sprintf("%s.rego", name),
			Mode: 0644,
			Size: int64(len(regoCode)),
		}
		if err := tw.WriteHeader(hdr); err != nil {
			log.Printf("Error writing file header for %s: %v", name, err)
			continue
		}
		if _, err := tw.Write([]byte(regoCode)); err != nil {
			log.Printf("Error writing file body for %s: %v", name, err)
			continue
		}
	}

	// Close writers to finalize the archive
	if err := tw.Close(); err != nil {
		log.Printf("Error closing tar writer: %v", err)
	}
	if err := gw.Close(); err != nil {
		log.Printf("Error closing gzip writer: %v", err)
	}

	w.Header().Set("Content-Type", "application/gzip")
	w.Header().Set("Content-Disposition", "attachment; filename=\"policies.tar.gz\"")
	w.Write(buf.Bytes())
}

// Helper to get environment variables with a default value
func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}
