import simplekml
import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

def geocode_address(address):
    geolocator = Nominatim(user_agent="my_kml_generator")
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            print("Address not found. Please try again.")
            return None
    except (GeocoderTimedOut, GeocoderServiceError):
        print("Geocoding service timed out or error occurred. Please try again.")
        return None

def generate_circle_coords(center, radius, num_points=36):
    lat, lon = center
    coords = []
    for i in range(num_points):
        angle = math.radians(float(i) / num_points * 360.0)
        dx = radius * math.cos(angle)
        dy = radius * math.sin(angle)
        point_lat = lat + (dy / 111111)  # 1 degree of latitude = 111111 meters
        point_lon = lon + (dx / (111111 * math.cos(math.radians(lat))))
        coords.append((point_lon, point_lat))  # Note: KML uses (lon, lat) order
    coords.append(coords[0])  # Close the polygon
    return coords

def generate_square_coords(center, side_length):
    lat, lon = center
    half_side = side_length / 2
    d_lat = half_side / 111111
    d_lon = half_side / (111111 * math.cos(math.radians(lat)))
    return [
        (lon - d_lon, lat + d_lat),
        (lon + d_lon, lat + d_lat),
        (lon + d_lon, lat - d_lat),
        (lon - d_lon, lat - d_lat),
        (lon - d_lon, lat + d_lat)  # Close the polygon
    ]

def generate_triangle_coords(center, side_length):
    lat, lon = center
    height = side_length * (math.sqrt(3) / 2)
    d_lat = height / (3 * 111111)
    d_lon = side_length / (2 * 111111 * math.cos(math.radians(lat)))
    return [
        (lon, lat + 2*d_lat),
        (lon - d_lon, lat - d_lat),
        (lon + d_lon, lat - d_lat),
        (lon, lat + 2*d_lat)  # Close the polygon
    ]

def create_polygon_kml(polygon_type, center, size, height, fill_color, fill_opacity, outline_color, outline_width, output_file):
    kml = simplekml.Kml()
    pol = kml.newpolygon(name=f"My {polygon_type.capitalize()}")

    if polygon_type == "circle":
        coords = generate_circle_coords(center, size)
    elif polygon_type == "square":
        coords = generate_square_coords(center, size)
    elif polygon_type == "triangle":
        coords = generate_triangle_coords(center, size)
    else:
        raise ValueError("Invalid polygon type. Choose 'circle', 'square', or 'triangle'.")

    pol.outerboundaryis = coords
    pol.altitudemode = simplekml.AltitudeMode.relativetoground
    pol.extrude = 1
    
    # Set polygon style
    pol.style.polystyle.color = simplekml.Color.changealphaint(int(fill_opacity * 255), fill_color)
    pol.style.polystyle.outline = 1
    pol.style.linestyle.color = outline_color
    pol.style.linestyle.width = outline_width

    # Set polygon height
    for coord in pol.outerboundaryis.coords:
        coord[2] = height  # Set the altitude for each coordinate

    # Add a LookAt view to ensure Google Earth focuses on the polygon
    lookat = simplekml.LookAt()
    lookat.longitude, lookat.latitude = center[1], center[0]
    lookat.altitude = height / 2  # Set the camera altitude to half the polygon height
    lookat.range = size * 3  # Adjust the view to show an area 3 times the size of the polygon
    lookat.heading = 0
    lookat.tilt = 60  # Tilt the view for better 3D perception
    pol.lookat = lookat

    kml.save(output_file)
    print(f"KML file '{output_file}' has been created.")

def get_color_input(prompt):
    color_map = {
        'red': simplekml.Color.red,
        'green': simplekml.Color.green,
        'blue': simplekml.Color.blue,
        'white': simplekml.Color.white,
        'black': simplekml.Color.black,
        'yellow': simplekml.Color.yellow,
        'cyan': simplekml.Color.cyan,
        'magenta': simplekml.Color.magenta
    }
    while True:
        color = input(prompt).lower()
        if color in color_map:
            return color_map[color]
        print("Invalid color. Please choose from red, green, blue, white, black, yellow, cyan, or magenta.")

def main():
    address = input("Enter a street address: ")
    center = geocode_address(address)
    
    if center:
        print(f"Coordinates: {center}")
        
        while True:
            polygon_type = input("Enter polygon type (circle, square, or triangle): ").lower()
            if polygon_type in ["circle", "square", "triangle"]:
                break
            print("Invalid polygon type. Please choose circle, square, or triangle.")
        
        size = float(input("Enter size in meters (radius for circle, side length for square/triangle): "))
        height = float(input("Enter height of the polygon in meters: "))
        
        fill_color = get_color_input("Enter fill color (red, green, blue, white, black, yellow, cyan, magenta): ")
        fill_opacity = float(input("Enter fill opacity (0.0 to 1.0): "))
        outline_color = get_color_input("Enter outline color (red, green, blue, white, black, yellow, cyan, magenta): ")
        outline_width = float(input("Enter outline width in pixels: "))
        
        output_file = f"{polygon_type}_at_{address.replace(' ', '_')}.kml"
        create_polygon_kml(polygon_type, center, size, height, fill_color, fill_opacity, outline_color, outline_width, output_file)

if __name__ == "__main__":
    main()
