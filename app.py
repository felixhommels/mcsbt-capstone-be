from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.user_routes import router as user_router
from routes.flights_routes import router as flight_router
from routes.statistics_routes import router as statistics_router
from routes.route_info import router as route_info_router
import uvicorn

app = FastAPI()

app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Allow all origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )

app.include_router(user_router, tags=["User"])
app.include_router(flight_router, tags=["Flights"])
app.include_router(statistics_router, tags=["Statistics"])
app.include_router(route_info_router, tags=["Route Info"])

@app.get("/")
def root():
    return {"message": "SkyLedger API Running"}

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
    